#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { CdkBedrockAgentQueryMysqlStack } from '../lib/cdk-bedrock-agent-query-mysql-stack';

const app = new cdk.App();
new CdkBedrockAgentQueryMysqlStack(app, 'CdkBedrockAgentQueryMysqlStack', {
  description: 'Demo Bedrock Agent to query RDS MySQL',
  env: {
    region: process.env.CDK_DEFAULT_REGION,
    account: process.env.CDK_DEFAULT_ACCOUNT,
  }
});