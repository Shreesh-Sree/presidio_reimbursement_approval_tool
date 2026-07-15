module "network" {
  source = "./modules/network"

  name_prefix          = local.name_prefix
  vpc_cidr             = var.vpc_cidr
  availability_zones   = local.availability_zones
  aws_region           = var.aws_region
  allowed_ingress_cidr = var.allowed_ingress_cidr
  tags                 = local.common_tags
}

module "storage" {
  source = "./modules/storage"

  uploads_bucket_name = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-uploads"
  static_bucket_name  = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-web"
  force_destroy       = var.allow_bucket_force_destroy
  tags                = local.common_tags
}

module "registry" {
  source = "./modules/registry"

  name_prefix = local.name_prefix
  tags        = local.common_tags
}

module "logging" {
  source = "./modules/logging"

  name_prefix       = local.name_prefix
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

module "credentials" {
  source = "./modules/credentials"

  name_prefix = local.name_prefix
  tags        = local.common_tags
}

module "database" {
  source = "./modules/database"

  name_prefix                = local.name_prefix
  private_subnet_ids         = module.network.private_database_subnet_ids
  database_security_group_id = module.network.database_security_group_id
  availability_zone          = local.availability_zones[0]
  instance_class             = var.postgres_instance_class
  allocated_storage_gib      = var.postgres_allocated_storage_gib
  max_allocated_storage_gib  = var.postgres_max_allocated_storage_gib
  engine_version             = var.postgres_engine_version
  master_password            = module.credentials.database_password
  deletion_protection        = var.rds_deletion_protection
  skip_final_snapshot        = var.rds_skip_final_snapshot
  tags                       = local.common_tags

  depends_on = [module.logging]
}

module "mail" {
  source = "./modules/mail"

  domain_name     = var.domain_name
  route53_zone_id = var.route53_zone_id
  aws_region      = var.aws_region
  tags            = local.common_tags
}

module "app_config" {
  source = "./modules/app_config"

  application_secret_arn              = module.credentials.application_secret_arn
  ai_review_secret_arn                = module.credentials.ai_review_secret_arn
  receipt_intelligence_secret_arn     = module.credentials.receipt_intelligence_secret_arn
  policy_assistant_secret_arn         = module.credentials.policy_assistant_secret_arn
  database_host                       = module.database.address
  database_port                       = module.database.port
  database_name                       = module.database.database_name
  database_username                   = module.database.master_username
  database_password                   = module.credentials.database_password
  jwt_secret                          = module.credentials.jwt_secret
  ai_service_token                    = module.credentials.ai_service_token
  ai_review_reference_hmac_key        = module.credentials.ai_review_reference_hmac_key
  receipt_intelligence_service_token  = module.credentials.receipt_intelligence_service_token
  policy_assistant_service_token      = module.credentials.policy_assistant_service_token
  policy_assistant_reference_hmac_key = module.credentials.policy_assistant_reference_hmac_key
  aws_region                          = var.aws_region
  uploads_bucket_name                 = module.storage.uploads_bucket_name
  app_domain                          = local.app_domain
  smtp_host                           = module.mail.smtp_endpoint
  smtp_from                           = module.mail.sender_email
  email_delivery_enabled              = var.enable_email_delivery
  smtp_username                       = var.ses_smtp_username
  smtp_password                       = var.ses_smtp_password
  gemini_api_key                      = var.gemini_api_key
  groq_api_key                        = var.groq_api_key
  ai_review_provider                  = var.ai_review_provider
  groq_model                          = var.groq_model
  clerk_jwks_url                      = var.clerk_jwks_url
  clerk_issuer                        = var.clerk_issuer
  clerk_audience                      = var.clerk_audience
  clerk_authorized_parties            = var.clerk_authorized_parties
  super_admin_email                   = var.super_admin_email
  default_organization_name           = var.default_organization_name
  default_organization_code           = var.default_organization_code
  default_department_name             = var.default_department_name
  default_department_code             = var.default_department_code
}

module "runtime" {
  source = "./modules/runtime"

  name_prefix                         = local.name_prefix
  ami_id                              = data.aws_ssm_parameter.amazon_linux_2023.value
  instance_type                       = var.ec2_instance_type
  root_volume_gib                     = var.ec2_root_volume_gib
  public_subnet_id                    = module.network.public_subnet_ids[0]
  app_security_group_id               = module.network.application_security_group_id
  application_secret_arn              = module.credentials.application_secret_arn
  ai_review_secret_arn                = module.credentials.ai_review_secret_arn
  receipt_intelligence_secret_arn     = module.credentials.receipt_intelligence_secret_arn
  policy_assistant_secret_arn         = module.credentials.policy_assistant_secret_arn
  uploads_bucket_arn                  = module.storage.uploads_bucket_arn
  api_repository_arn                  = module.registry.api_repository_arn
  ai_repository_arn                   = module.registry.ai_repository_arn
  receipt_intelligence_repository_arn = module.registry.receipt_intelligence_repository_arn
  policy_assistant_repository_arn     = module.registry.policy_assistant_repository_arn
  api_repository_url                  = module.registry.api_repository_url
  ai_repository_url                   = module.registry.ai_repository_url
  receipt_intelligence_repository_url = module.registry.receipt_intelligence_repository_url
  policy_assistant_repository_url     = module.registry.policy_assistant_repository_url
  ecr_registry_url                    = module.registry.registry_url
  aws_region                          = var.aws_region
  api_domain                          = local.api_domain
  acme_email                          = var.acme_email
  api_log_group_name                  = module.logging.api_log_group_name
  ai_log_group_name                   = module.logging.ai_log_group_name
  receipt_intelligence_log_group_name = module.logging.receipt_intelligence_log_group_name
  policy_assistant_log_group_name     = module.logging.policy_assistant_log_group_name
  proxy_log_group_name                = module.logging.proxy_log_group_name
  api_log_group_arn                   = module.logging.api_log_group_arn
  ai_log_group_arn                    = module.logging.ai_log_group_arn
  receipt_intelligence_log_group_arn  = module.logging.receipt_intelligence_log_group_arn
  policy_assistant_log_group_arn      = module.logging.policy_assistant_log_group_arn
  proxy_log_group_arn                 = module.logging.proxy_log_group_arn
  tags                                = local.common_tags

  depends_on = [module.app_config]
}

module "edge" {
  source = "./modules/edge"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  app_domain                         = local.app_domain
  api_domain                         = local.api_domain
  api_ipv4                           = module.runtime.public_ip
  route53_zone_id                    = var.route53_zone_id
  static_bucket_id                   = module.storage.static_bucket_id
  static_bucket_arn                  = module.storage.static_bucket_arn
  static_bucket_regional_domain_name = module.storage.static_bucket_regional_domain_name
  name_prefix                        = local.name_prefix
  tags                               = local.common_tags
}

module "alerts" {
  source = "./modules/alerts"

  name_prefix         = local.name_prefix
  notification_email  = var.budget_alert_email
  instance_id         = module.runtime.instance_id
  database_identifier = module.database.identifier
  tags                = local.common_tags
}

module "cost_guard" {
  source = "./modules/cost_guard"

  name_prefix        = local.name_prefix
  limit_amount_usd   = var.monthly_budget_limit_usd
  notification_email = var.budget_alert_email
}
