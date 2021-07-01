from aws_cdk import core as cdk, aws_ec2 as ec2, aws_logs as cloudwatch_logs
import boto3
import botocore
import sys


class NoDomainCertificateError(Exception):
    pass


class VpnStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, id: str, vpc=ec2.IVpc, **kwargs) -> None:
        super().__init__(scope=scope, id=id, **kwargs)

        try:
            server_certificate_arn = self.__get_certificate_arn_from_acm("acme.com")
            client_certificate_arn = self.__get_certificate_arn_from_acm(
                "client.acme.com"
            )
        except botocore.exceptions.ClientError as error:
            print(error)
        except NoDomainCertificateError:
            try:
                self.__import_certificates()
                server_certificate_arn = self.__get_certificate_arn_from_acm("acme.com")
                client_certificate_arn = self.__get_certificate_arn_from_acm(
                    "client.acme.com"
                )
            except botocore.exceptions.ClientError as error:
                print(error)
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise

        cidr = "10.20.0.0/16"

        infrastructure_subnets = ec2.SubnetSelection(subnet_group_name="infrastructure")

        security_group = ec2.SecurityGroup(self, "security-group", vpc=vpc)
        security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4("10.0.0.0/8"), connection=ec2.Port.tcp(443)
        )

        log_group = cloudwatch_logs.LogGroup(
            self,
            "log-group",
            log_group_name="client-vpn",
            retention=cloudwatch_logs.RetentionDays.ONE_WEEK,
        )

        self.client_vpn = ec2.ClientVpnEndpoint(
            self,
            "client-vpn",
            vpc=vpc,
            cidr=cidr,
            server_certificate_arn=server_certificate_arn,
            client_certificate_arn=client_certificate_arn,
            vpc_subnets=infrastructure_subnets,
            security_groups=[security_group],
            split_tunnel=True,
            log_group=log_group,
        )

    def __get_certificate_arn_from_acm(self, domain_name: str) -> str:
        acm = boto3.client("acm")
        response = acm.list_certificates()
        certificates = response["CertificateSummaryList"]

        if len(certificates) == 0:
            raise NoDomainCertificateError

        result = [cert for cert in certificates if cert["DomainName"] == domain_name]
        if len(result) == 0:
            raise NoDomainCertificateError
        return result[0]["CertificateArn"]

    def __import_certificates(self):
        certificate_authority = self.__file_content_binary("./acm/ca.crt")

        server_certificate = self.__file_content_binary("./acm/acme.com.crt")
        server_certificate_key = self.__file_content_binary("./acm/acme.com.key")

        client_certificate = self.__file_content_binary("./acm/client.acme.com.crt")
        client_certificate_key = self.__file_content_binary("./acm/client.acme.com.key")

        acm = boto3.client("acm")

        # import server certificate
        acm.import_certificate(
            Certificate=server_certificate,
            PrivateKey=server_certificate_key,
            CertificateChain=certificate_authority,
        )

        # import client certificate
        acm.import_certificate(
            Certificate=client_certificate,
            PrivateKey=client_certificate_key,
            CertificateChain=certificate_authority,
        )

    def __file_content_binary(self, filename: str) -> bytes:
        try:
            with open(filename, mode="rb") as f:
                return f.read()
        except Exception as e:
            print(e)
