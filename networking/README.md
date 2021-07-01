# Networking

To setup a shared VPC, that can be shared across multiple AWS accounts, we need to [enable trusted access with AWS RAM service](https://docs.aws.amazon.com/organizations/latest/userguide/services-that-can-integrate-ram.html#integrate-enable-ta-ram) for AWS Organization. 

```
aws organizations enable-aws-service-access --service-principal ram.amazonaws.com
```
