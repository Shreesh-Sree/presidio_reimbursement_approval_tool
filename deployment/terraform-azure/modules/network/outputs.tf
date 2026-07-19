output "container_apps_subnet_id" {
  description = "Dedicated subnet ID used for Container Apps infrastructure and private DNS resolution."
  value       = azurerm_subnet.container_apps.id
}

output "private_endpoint_subnet_id" {
  description = "Dedicated subnet ID used by private endpoints."
  value       = azurerm_subnet.private_endpoints.id
}

output "private_dns_zone_ids" {
  description = "Private DNS zone IDs keyed by service name."
  value = {
    for key, zone in azurerm_private_dns_zone.main : key => zone.id
  }
}

output "virtual_network_id" {
  description = "Private virtual network resource ID."
  value       = azurerm_virtual_network.main.id
}
