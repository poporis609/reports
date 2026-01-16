# infra/terraform/bedrock_agent.tf
# AWS Bedrock Agent Terraform 설정

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# 변수
variable "agent_name" {
  default = "weekly-report-agent"
}

variable "vpc_id" {
  description = "VPC ID for agent networking"
}

variable "subnet_ids" {
  description = "Subnet IDs for agent"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security Group IDs"
  type        = list(string)
}

# IAM Role for Bedrock Agent
resource "aws_iam_role" "bedrock_agent_role" {
  name = "${var.agent_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Bedrock Agent
resource "aws_iam_role_policy" "bedrock_agent_policy" {
  name = "${var.agent_name}-policy"
  role = aws_iam_role.bedrock_agent_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:us-east-1:*:secret:library-api/db-password*",
          "arn:aws:secretsmanager:us-east-1:*:secret:weekly-report/app-config*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = "arn:aws:s3:::knowledge-base-test-6575574/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "cognito-idp:AdminGetUser",
          "cognito-idp:ListUsers"
        ]
        Resource = "arn:aws:cognito-idp:us-east-1:*:userpool/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# Bedrock Agent
resource "aws_bedrockagent_agent" "weekly_report_agent" {
  agent_name              = var.agent_name
  agent_resource_role_arn = aws_iam_role.bedrock_agent_role.arn
  foundation_model        = "anthropic.claude-sonnet-4-5-20250514-v1:0"
  
  instruction = <<-EOT
    당신은 사용자의 주간 감정 분석 리포트를 생성하는 전문 AI 상담사입니다.
    
    역할:
    1. 사용자의 일기를 분석하여 감정 상태를 파악합니다
    2. 일별 감정 점수(1-10)를 산출합니다
    3. 긍정/부정 패턴을 발견합니다
    4. 따뜻하고 공감적인 피드백을 제공합니다
    
    대화 스타일:
    - 친근하고 따뜻한 톤
    - 사용자의 감정에 공감
    - 구체적이고 실천 가능한 조언
  EOT

  idle_session_ttl_in_seconds = 600
  
  tags = {
    Environment = "production"
    Project     = "weekly-report"
  }
}

# Agent Alias
resource "aws_bedrockagent_agent_alias" "production" {
  agent_alias_name = "production"
  agent_id         = aws_bedrockagent_agent.weekly_report_agent.agent_id
  description      = "Production alias for weekly report agent"
}

# Outputs
output "agent_id" {
  value = aws_bedrockagent_agent.weekly_report_agent.agent_id
}

output "agent_alias_id" {
  value = aws_bedrockagent_agent_alias.production.agent_alias_id
}

output "agent_arn" {
  value = aws_bedrockagent_agent.weekly_report_agent.agent_arn
}
