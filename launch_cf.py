#!/usr/bin/python
# Converted from VPC_With_VPN_Connection.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates
import boto3
from troposphere import (
    Parameter,
    Ref,
    Tags,
    Template,
)
from troposphere.ec2 import (
    VPC,
    Instance,
    InternetGateway,
    NetworkAcl,
    NetworkAclEntry,
    NetworkInterfaceProperty,
    PortRange,
    Route,
    RouteTable,
    SecurityGroup,
    SecurityGroupRule,
    Subnet,
    SubnetNetworkAclAssociation,
    SubnetRouteTableAssociation,
    VPCGatewayAttachment,
)

t = Template()

t.set_version("2010-09-09")

t.set_description(
    """\
AWS CloudFormation Template VPC_Single_Instance_In_Subnet: Sample \
template showing how to create a VPC and add an EC2 instance in a Private Subnet"""
)

keyname_param = t.add_parameter(
    Parameter(
        "KeyPair",
        ConstraintDescription="must be the name of an existing EC2 KeyPair.",
        Description="Name of an existing EC2 KeyPair to enable SSH access to \
the instance",
        Default="vockey",
        Type="AWS::EC2::KeyPair::KeyName",
    )
)

image_id = t.add_parameter(
    Parameter(
        "AmazonLinuxAMIID",
        Type="AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>",
        Default="/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2",
    )
)

sshlocation_param = t.add_parameter(
    Parameter(
        "SSHLocation",
        Description=" The IP address range that can be used to SSH to the EC2 \
instances",
        Type="String",
        MinLength="9",
        MaxLength="18",
        Default="0.0.0.0/0",
        AllowedPattern=r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})",
        ConstraintDescription="must be a valid IP CIDR range of the form x.x.x.x/x.",
    )
)

ref_stack_id = Ref("AWS::StackId")

VPCResource = t.add_resource(
    VPC("VPC", CidrBlock="10.0.0.0/16", Tags=Tags(Application=ref_stack_id))
)

publicSubnet = t.add_resource(
    Subnet(
        "PublicSubnet",
        CidrBlock="10.0.0.0/24",
        VpcId=Ref(VPCResource),
        Tags=Tags(Application=ref_stack_id),
    )
)

privateSubnet = t.add_resource(
    Subnet(
        "PrivateSubnet",
        CidrBlock="10.0.1.0/24",
        VpcId=Ref(VPCResource),
        Tags=Tags(Application=ref_stack_id),
    )
)

internetGateway = t.add_resource(
    InternetGateway("InternetGateway", Tags=Tags(Application=ref_stack_id))
)

gatewayAttachment = t.add_resource(
    VPCGatewayAttachment(
        "AttachGateway", VpcId=Ref(VPCResource), InternetGatewayId=Ref(internetGateway)
    )
)

publicRouteTable = t.add_resource(
    RouteTable(
        "publicRouteTable", VpcId=Ref(VPCResource), Tags=Tags(Application=ref_stack_id)
    )
)

privateRouteTable = t.add_resource(
    RouteTable(
        "privateRouteTable", VpcId=Ref(VPCResource), Tags=Tags(Application=ref_stack_id)
    )
)

routeInternetGateway = t.add_resource(
    Route(
        "RouteInternetGateway",
        DependsOn="AttachGateway",
        GatewayId=Ref("InternetGateway"),
        DestinationCidrBlock="0.0.0.0/0",
        RouteTableId=Ref(publicRouteTable),
    )
)

pubSubnetRouteTableAssociation = t.add_resource(
    SubnetRouteTableAssociation(
        "publicSubnetRouteTableAssociation",
        SubnetId=Ref(publicSubnet),
        RouteTableId=Ref(publicRouteTable),
    )
)

priSubnetRouteTableAssociation = t.add_resource(
    SubnetRouteTableAssociation(
        "privateSubnetRouteTableAssociation",
        SubnetId=Ref(privateSubnet),
        RouteTableId=Ref(privateRouteTable),
    )
)

networkAcl = t.add_resource(
    NetworkAcl(
        "NetworkAcl",
        VpcId=Ref(VPCResource),
        Tags=Tags(Application=ref_stack_id),
    )
)

inboundSSHNetworkAclEntry = t.add_resource(
    NetworkAclEntry(
        "InboundSSHNetworkAclEntry",
        NetworkAclId=Ref(networkAcl),
        RuleNumber="101",
        Protocol="6",
        PortRange=PortRange(To="22", From="22"),
        Egress="false",
        RuleAction="allow",
        CidrBlock="0.0.0.0/0",
    )
)

pubSubnetNetworkAclAssociation = t.add_resource(
    SubnetNetworkAclAssociation(
        "publicSubnetNetworkAclAssociation",
        SubnetId=Ref(publicSubnet),
        NetworkAclId=Ref(networkAcl),
    )
)

priSubnetNetworkAclAssociation = t.add_resource(
    SubnetNetworkAclAssociation(
        "privateSubnetNetworkAclAssociation",
        SubnetId=Ref(privateSubnet),
        NetworkAclId=Ref(networkAcl),
    )
)

instanceSecurityGroup = t.add_resource(
    SecurityGroup(
        "InstanceSecurityGroup",
        GroupDescription="Enable SSH access via port 22",
        SecurityGroupIngress=[
            SecurityGroupRule(
                IpProtocol="tcp",
                FromPort="22",
                ToPort="22",
                CidrIp=Ref(sshlocation_param),
            ),
            SecurityGroupRule(
                IpProtocol="tcp", FromPort="80", ToPort="80", CidrIp="0.0.0.0/0"
            ),
        ],
        VpcId=Ref(VPCResource),
    )
)

instance = t.add_resource(
    Instance(
        "EC2Instance",
        ImageId=Ref(image_id),
        InstanceType="t3.micro",
        KeyName=Ref(keyname_param),
        NetworkInterfaces=[
            NetworkInterfaceProperty(
                GroupSet=[Ref(instanceSecurityGroup)],
                DeviceIndex="0",
                DeleteOnTermination="true",
                SubnetId=Ref(privateSubnet),
            )
        ],
        Tags=Tags(Application=ref_stack_id, Name="Private Instance"),
    )
)

template_file = t.to_json()

sess = boto3.Session(region_name="us-west-2")

cloudformation_client = sess.client('cloudformation')

cloudformation_client.create_stack(StackName='LabStack', TemplateBody=template_file)
