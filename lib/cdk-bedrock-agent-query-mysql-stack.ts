import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as customresource from 'aws-cdk-lib/custom-resources';
import { readFileSync } from 'fs';

export class CdkBedrockAgentQueryMysqlStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const dbuser = 'dbuser'
    const dbname = 'employees'

    const vpc = new ec2.Vpc(this, 'VPC', {
      ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
      natGateways: 1,
      maxAzs: 2,
      subnetConfiguration: [
        {
          name: 'public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: 'private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        },
      ],
    });

    // create database subnet group with private subnet
    const subnetGroup = new rds.SubnetGroup(this, 'SubnetGroup', {
      vpc: vpc,
      description: 'subnet group for rds',
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
    });

    // create security group for mysql port accept for all vpc ip
    const dbsecurityGroup = new ec2.SecurityGroup(this, 'RdsSecurityGroup', {
      vpc: vpc,
      description: 'security group for rds',
      allowAllOutbound: true,
    });
    dbsecurityGroup.addIngressRule(ec2.Peer.ipv4(vpc.vpcCidrBlock), ec2.Port.tcp(3306), 'accept all mysql port');

    // create rds password in secret manager
    const secret = new secretsmanager.Secret(this, 'Secret', {
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          username: dbuser,
        }),
        excludePunctuation: true,
        includeSpace: false,
        passwordLength: 16,
        generateStringKey: 'password',
      },
    });

    // create rds mysql versi 8 with db subnet group and security group above
    const rdsInstance = new rds.DatabaseInstance(this, 'RDS', {
      engine: rds.DatabaseInstanceEngine.mysql({
        version: rds.MysqlEngineVersion.VER_8_0_35,
      }),
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T4G, ec2.InstanceSize.LARGE),
      allocatedStorage: 20,
      vpc: vpc,
      subnetGroup: subnetGroup,
      securityGroups: [ dbsecurityGroup ],
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      credentials: rds.Credentials.fromSecret(secret),
      databaseName: dbname,
      port: 3306,
      multiAz: false,
      maxAllocatedStorage: 500,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      enablePerformanceInsights: true,
    });

    // Crete lambda security group
    const lambdaSecurityGroup = new ec2.SecurityGroup(this, 'LambdaSecurityGroup', {
      vpc: vpc,
      description: 'security group for lambda',
      allowAllOutbound: true,
    });
    dbsecurityGroup.addEgressRule(lambdaSecurityGroup, ec2.Port.tcp(3306), 'Allow MySQL Access')

    // create lambda role
    const lambdaRole = new iam.Role(this, 'LambdaRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      inlinePolicies: {
        'getSecret': new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              actions: ['secretsmanager:GetSecretValue'],
              resources: [secret.secretArn],
            }),
          ],
        }),
      },
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    // create lambda layer from folder lambdaLayer
    const lambdaLayer = new lambda.LayerVersion(this, 'LambdaLayer', {
      code: lambda.Code.fromAsset('lambdaLayer'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
      description: 'Layer for lambda',
    });

    // create lambda function with vpc and rds access
    const lambdaLoader = new lambda.Function(this, 'lambdaLoader', {
      runtime: lambda.Runtime.PYTHON_3_12,
      code: lambda.Code.fromAsset('lambdaLoader'),
      handler: 'app.lambda_handler',
      vpc: vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [ lambdaSecurityGroup ],
      environment: {
        db_host: rdsInstance.dbInstanceEndpointAddress,
        db_port: '3306',
        db_user: dbuser,
        db_password_secret: secret.secretName,
        db_name: dbname
      },
      role: lambdaRole,
      layers: [ lambdaLayer ],
      timeout: cdk.Duration.seconds(600),
      architecture: lambda.Architecture.ARM_64,
      memorySize: 10240
    });

    // create custom resource provider
    const customResourceProvider = new customresource.Provider(this, 'CustomResourceProvider', {
      onEventHandler: lambdaLoader,
      logRetention: logs.RetentionDays.ONE_DAY
    });
    customResourceProvider.node.addDependency(rdsInstance)

    // create custom resource 
    const customResourceCall = new cdk.CustomResource(this, 'CustomResourceCall', {
      serviceToken: customResourceProvider.serviceToken,
    })

    // Create IAM Role
    const role = new iam.Role(this, 'ec2role', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess')
      ]
    });

    // Create EC2 Instance
    const instance = new ec2.Instance(this, 'ec2instance', {
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.T4G,
        ec2.InstanceSize.MEDIUM
      ),
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      machineImage: new ec2.AmazonLinuxImage({
        cpuType: ec2.AmazonLinuxCpuType.ARM_64,
        generation: ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
      }),
      role,
    })

    // Add EC2 userdata
    const userData = readFileSync('./lib/userdata.sh', 'utf8');
    instance.addUserData(userData);

    // create lambda function for Bedrock Agent with vpc and rds access
    const lambdaBedrockAgent = new lambda.Function(this, 'lambdaBedrockAgent', {
      runtime: lambda.Runtime.PYTHON_3_12,
      code: lambda.Code.fromAsset('lambdaBedrockAgent'),
      handler: 'app.lambda_handler',
      vpc: vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      },
      securityGroups: [ lambdaSecurityGroup ],
      environment: {
        db_host: rdsInstance.dbInstanceEndpointAddress,
        db_port: '3306',
        db_user: dbuser,
        db_password_secret: secret.secretName,
        db_name: dbname
      },
      role: lambdaRole,
      layers: [ lambdaLayer ],
      timeout: cdk.Duration.seconds(600),
      architecture: lambda.Architecture.ARM_64,
      memorySize: 1024
    });
    lambdaBedrockAgent.node.addDependency(rdsInstance)

    // Lambda resource policy for Bedrock
    const lambdaResourcePermission = new lambda.CfnPermission(this, 'lambdaResourcePermission', {
      functionName: lambdaBedrockAgent.functionName,
      principal: 'bedrock.amazonaws.com',
      action: 'lambda:InvokeFunction',
      sourceAccount: this.account, 
      sourceArn: `arn:aws:bedrock:${this.region}:${this.account}:agent/*`
    });

    // output vpc id
    new cdk.CfnOutput(this, 'VPCId', {value: vpc.vpcId});
    // output rds endpoint
    new cdk.CfnOutput(this, 'RDSInstanceEndpoint', { value: rdsInstance.dbInstanceEndpointAddress }); 
    // output secret name
    new cdk.CfnOutput(this, 'SecretName', { value: secret.secretName }); 
    // output lambda function name
    new cdk.CfnOutput(this, 'LambdaFunctionArn', { value: lambdaLoader.functionArn});
    // output ec2 id
    new cdk.CfnOutput(this, 'EC2Id', { value: instance.instanceId});
    // output lambda function name for Bedrock Agent
    new cdk.CfnOutput(this, 'LambdaBedrockAgentFunctionArn', { value: lambdaBedrockAgent.functionArn});
  }
}
