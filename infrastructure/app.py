#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from infrastructure.infrastructure_stack import InfrastructureStack
from infrastructure.jenkins_stack import JenkinsStack

from dotenv import load_dotenv

load_dotenv()

app = cdk.App()
infrastucture = InfrastructureStack(
    app,
    "infrastructure",
    os.getenv("VPC_ID"),
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.
    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.
    # env=core.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */
    env=cdk.Environment(account=os.getenv("AWS_ACCOUNT"), region=os.getenv("AWS_REGION")),
    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
)

jenkins_props = {
    "alb_subnet_1": os.getenv("INFRASTRUCTURE_SUBNET_1"),
    "alb_subnet_2": os.getenv("INFRASTRUCTURE_SUBNET_2"),
    "jenkins_subnet_1": os.getenv("JENKINS_SUBNET_1"),
    "jenkins_subnet_2": os.getenv("JENKINS_SUBNET_2"),
    "vpn_client_cidr": os.getenv("VPN_CLIENT_CIDR"),
    "admin_password": os.getenv("ADMIN_PASSWORD"),
}

JenkinsStack(
    app,
    "jenkins",
    infrastucture.cluster,
    jenkins_props,
    env=cdk.Environment(account=os.getenv("AWS_ACCOUNT"), region=os.getenv("AWS_REGION")),
)

app.synth()
