from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_sqs as sqs,
    aws_dynamodb as dynamodb,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_ecs_patterns as ecs_patterns,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
    aws_events as events,
    aws_events_targets as events_targets,
)
from constructs import Construct

class InfrastructureStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Configurable parameters via CDK context
        jira_base_url = self.node.try_get_context("jira_base_url") or "https://nguyenminhtung.atlassian.net"
        jira_email = self.node.try_get_context("jira_email") or "nguyenminhtung.developer@gmail.com"
        target_repo = self.node.try_get_context("target_repo") or "TeaSui/swarmforge-session-dashboard"

        # 1. DynamoDB Tables
        idempotency_table = dynamodb.Table(
            self, "IdempotencyTable",
            table_name="swarmforge-idempotency",
            partition_key=dynamodb.Attribute(name="idempotency_key", type=dynamodb.AttributeType.STRING),
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        tasks_table = dynamodb.Table(
            self, "TasksTable",
            table_name="swarmforge-tasks",
            partition_key=dynamodb.Attribute(name="task_id", type=dynamodb.AttributeType.STRING),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # 2. SQS Queues
        events_dlq = sqs.Queue(
            self, "EventsDLQ",
            queue_name="swarmforge-events-dlq",
            retention_period=Duration.days(14),
        )

        events_queue = sqs.Queue(
            self, "EventsQueue",
            queue_name="swarmforge-events",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(7),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=events_dlq,
            ),
        )

        # 3. VPC and ECS Cluster
        vpc = ec2.Vpc(self, "SwarmForgeVpc", max_azs=2)
        cluster = ecs.Cluster(self, "SwarmForgeCluster", vpc=vpc)

        # 3.1 CloudWatch log groups
        api_log_group = logs.LogGroup(
            self,
            "ApiLogGroup",
            log_group_name="/swarmforge/ecs/api",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )
        worker_log_group = logs.LogGroup(
            self,
            "WorkerLogGroup",
            log_group_name="/swarmforge/ecs/worker",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )
        sla_log_group = logs.LogGroup(
            self,
            "SlaMonitorLogGroup",
            log_group_name="/swarmforge/ecs/sla-monitor",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )
        daily_rerun_log_group = logs.LogGroup(
            self,
            "DailyRerunLogGroup",
            log_group_name="/swarmforge/ecs/daily-rerun",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # 0. Secrets Manager (Consolidated Secrets)
        swarm_secrets = secretsmanager.Secret(
            self, "SwarmForgeSecrets",
            secret_name="SwarmForgeSecrets",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"JIRA_API_TOKEN":"placeholder","ANTHROPIC_API_KEY":"placeholder","GITHUB_TOKEN":"placeholder","JIRA_WEBHOOK_SECRET":"replace-with-long-random-secret"}',
                generate_string_key="RANDOM_PART"
            )
        )

        # Shared environment config for all services
        shared_env = {
            "APP_ENV": "production",
            "AWS_REGION": self.region,
            "AWS_DEFAULT_REGION": self.region,
            "SWARMFORGE_STRICT_STAGE_FAILURES": "true",
            "SWARMFORGE_PRIMARY_LLM": "bedrock",
            "SWARMFORGE_BEDROCK_MODEL_ID": "global.anthropic.claude-sonnet-4-6",
            "SWARMFORGE_CREW_LLM_TIMEOUT_SECONDS": "90",
            "SWARMFORGE_CREW_MAX_TOKENS": "800",
            "SWARMFORGE_CREW_MAX_RETRIES": "2",
            "SWARMFORGE_CREW_STAGE_ATTEMPTS": "3",
            "SWARMFORGE_CREW_STAGE_RETRY_BACKOFF_SECONDS": "5",
            "SWARMFORGE_CREW_FALLBACK_MODEL": "bedrock/us.amazon.nova-lite-v1:0",
            "CREWAI_TRACING_ENABLED": "false",
            "APPROVAL_POLL_INTERVAL_SECONDS": "15",
            "APPROVAL_TIMEOUT_SECONDS": "900",
            "JIRA_BASE_URL": jira_base_url,
            "JIRA_EMAIL": jira_email,
            "SWARMFORGE_TARGET_REPO": target_repo,
        }

        shared_secrets = {
            "JIRA_API_TOKEN": ecs.Secret.from_secrets_manager(swarm_secrets, "JIRA_API_TOKEN"),
            "ANTHROPIC_API_KEY": ecs.Secret.from_secrets_manager(swarm_secrets, "ANTHROPIC_API_KEY"),
            "GITHUB_TOKEN": ecs.Secret.from_secrets_manager(swarm_secrets, "GITHUB_TOKEN"),
            "JIRA_WEBHOOK_SECRET": ecs.Secret.from_secrets_manager(swarm_secrets, "JIRA_WEBHOOK_SECRET"),
        }

        # 4. Fargate Service - API
        api_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "ApiService",
            cluster=cluster,
            cpu=256,
            memory_limit_mib=512,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset("../"),
                container_port=8000,
                environment={
                    **shared_env,
                    "SQS_QUEUE_URL": events_queue.queue_url,
                    "DYNAMODB_IDEMPOTENCY_TABLE": idempotency_table.table_name,
                },
                secrets=shared_secrets,
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="SwarmForgeApi",
                    log_group=api_log_group,
                ),
            ),
            public_load_balancer=True
        )

        # 5. Fargate Service - Consumer
        consumer_task = ecs.FargateTaskDefinition(
            self, "ConsumerTask",
            cpu=256,
            memory_limit_mib=512,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
        )
        consumer_container = consumer_task.add_container(
            "ConsumerContainer",
            image=ecs.ContainerImage.from_asset("../"),
            environment={
                **shared_env,
                "SQS_QUEUE_URL": events_queue.queue_url,
                "DYNAMODB_IDEMPOTENCY_TABLE": idempotency_table.table_name,
            },
            secrets=shared_secrets,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="SwarmForgeConsumer",
                log_group=worker_log_group,
            ),
            command=["python", "worker.py"]
        )

        consumer_service = ecs.FargateService(
            self, "ConsumerService",
            cluster=cluster,
            task_definition=consumer_task,
            desired_count=1
        )

        # 5.1 Scheduled SLA monitor (every 30 minutes) to retrigger stalled Jira issues
        sla_monitor_task = ecs.FargateTaskDefinition(
            self,
            "SlaMonitorTask",
            cpu=256,
            memory_limit_mib=512,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
        )
        sla_monitor_task.add_container(
            "SlaMonitorContainer",
            image=ecs.ContainerImage.from_asset("../"),
            command=["python", "scripts/monitor_jira_sla.py"],
            environment={
                "APP_ENV": "production",
                "AWS_REGION": self.region,
                "JIRA_BASE_URL": jira_base_url,
                "JIRA_EMAIL": jira_email,
                "SWARMFORGE_JIRA_WEBHOOK_URL": f"http://{api_service.load_balancer.load_balancer_dns_name}/webhook/jira",
                "SLA_JIRA_PROJECT_KEY": "SCRUM",
                "SLA_JIRA_STATUSES": "To Do,In Progress,In Review",
                "SLA_THRESHOLD_HOURS": "6",
                "SLA_MAX_ISSUES": "100",
                "SLA_MAX_RETRIGGERS_PER_RUN": "10",
                "SLA_CHAIN_LABELS": "health-check-app",
            },
            secrets={
                "JIRA_API_TOKEN": ecs.Secret.from_secrets_manager(swarm_secrets, "JIRA_API_TOKEN"),
                "JIRA_WEBHOOK_SECRET": ecs.Secret.from_secrets_manager(swarm_secrets, "JIRA_WEBHOOK_SECRET"),
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="SwarmForgeSlaMonitor",
                log_group=sla_log_group,
            ),
        )

        sla_schedule_rule = events.Rule(
            self,
            "SlaMonitorScheduleRule",
            schedule=events.Schedule.rate(Duration.minutes(30)),
        )
        sla_schedule_rule.add_target(
            events_targets.EcsTask(
                cluster=cluster,
                task_definition=sla_monitor_task,
                task_count=1,
                subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                platform_version=ecs.FargatePlatformVersion.LATEST,
            )
        )

        # 5.2 Scheduled daily rerun job for health-check-app chain
        daily_rerun_task = ecs.FargateTaskDefinition(
            self,
            "DailyRerunTask",
            cpu=256,
            memory_limit_mib=512,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
        )
        daily_rerun_task.add_container(
            "DailyRerunContainer",
            image=ecs.ContainerImage.from_asset("../"),
            command=["python", "scripts/daily_health_check_rerun.py"],
            environment={
                "APP_ENV": "production",
                "AWS_REGION": self.region,
                "JIRA_BASE_URL": jira_base_url,
                "JIRA_EMAIL": jira_email,
                "SWARMFORGE_JIRA_WEBHOOK_URL": f"http://{api_service.load_balancer.load_balancer_dns_name}/webhook/jira",
                "DAILY_JIRA_PROJECT_KEY": "SCRUM",
                "DAILY_CHAIN_LABELS": "health-check-app",
                "DAILY_STATUS_FILTER": "To Do,In Progress,In Review",
                "DAILY_MAX_RERUNS": "20",
            },
            secrets={
                "JIRA_API_TOKEN": ecs.Secret.from_secrets_manager(swarm_secrets, "JIRA_API_TOKEN"),
                "JIRA_WEBHOOK_SECRET": ecs.Secret.from_secrets_manager(swarm_secrets, "JIRA_WEBHOOK_SECRET"),
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="SwarmForgeDailyRerun",
                log_group=daily_rerun_log_group,
            ),
        )

        daily_rerun_rule = events.Rule(
            self,
            "DailyHealthCheckRerunRule",
            schedule=events.Schedule.cron(minute="0", hour="1"),
        )
        daily_rerun_rule.add_target(
            events_targets.EcsTask(
                cluster=cluster,
                task_definition=daily_rerun_task,
                task_count=1,
                subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                platform_version=ecs.FargatePlatformVersion.LATEST,
            )
        )

        # 6. IAM Permissions
        events_queue.grant_send_messages(api_service.task_definition.task_role)
        events_queue.grant_consume_messages(consumer_task.task_role)
        idempotency_table.grant_read_write_data(api_service.task_definition.task_role)
        idempotency_table.grant_read_write_data(consumer_task.task_role)
        tasks_table.grant_read_write_data(consumer_task.task_role)

        # Allow agents to call Bedrock
        consumer_task.task_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    f"arn:aws:bedrock:*:{self.account}:inference-profile/*",
                    "arn:aws:bedrock:*::inference-profile/*",
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/global.anthropic.claude-sonnet-4-6",
                    f"arn:aws:bedrock:us-east-1:{self.account}:inference-profile/global.anthropic.claude-sonnet-4-6",
                    f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0",
                    f"arn:aws:bedrock:us-east-1:{self.account}:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0",
                    f"arn:aws:bedrock:{self.region}::inference-profile/global.anthropic.claude-sonnet-4-6",
                    "arn:aws:bedrock:us-east-1::inference-profile/global.anthropic.claude-sonnet-4-6",
                    f"arn:aws:bedrock:{self.region}::inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0",
                    "arn:aws:bedrock:us-east-1::inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0",
                    "arn:aws:bedrock:::foundation-model/anthropic.claude-sonnet-4-6",
                    f"arn:aws:bedrock:{self.region}::foundation-model/*",
                    "arn:aws:bedrock:us-east-1::foundation-model/*",
                ],
            )
        )

        CfnOutput(self, "ApiLogGroupName", value=api_log_group.log_group_name)
        CfnOutput(self, "WorkerLogGroupName", value=worker_log_group.log_group_name)
        CfnOutput(self, "SlaMonitorLogGroupName", value=sla_log_group.log_group_name)
        CfnOutput(self, "DailyRerunLogGroupName", value=daily_rerun_log_group.log_group_name)
        CfnOutput(self, "EventsDLQUrl", value=events_dlq.queue_url)
        CfnOutput(
            self,
            "ApiEndpoint",
            value=f"http://{api_service.load_balancer.load_balancer_dns_name}",
        )
