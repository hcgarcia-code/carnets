# Restricción de cumplimiento: Proveedor de KMS en la UE

Los datos de afiliación sindical son datos personales de trabajadores europeos, sujetos a RGPD.
Las claves de cifrado que los protegen **no pueden custodiarse fuera de la UE** sin análisis
formales de transferencia internacional (Decisión de Adecuación, Cláusulas Tipo Contractuales).

## Descartados

- **AWS KMS**: Servidores en EEUU. ✗
- **Azure Key Vault (por defecto)**: Datacenters en EEUU. ✗ Solo válido si se configura
  explícitamente `eastus` → cambiar a `westeurope` o `northeurope`.

## Opciones viables

| Opción | Dónde vive | Ventaja | Desventaja |
|--------|-----------|---------|-----------|
| **HashiCorp Vault autoalojado** | Tu infraestructura en EU | Controlado 100% por CGT; cero dependencias externas | Hay que operarlo |
| **Azure Key Vault en EU** | Datacenters Microsoft en EU | Respaldado por Microsoft; rotación automática | Depende de Microsoft; hay que auditar la configuración |

## Recomendación

**HashiCorp Vault autoalojado**. Es el único que garantiza que el material criptográfico nunca
sale del control de CGT, y es viable en la infraestructura actual.

Implementación en `deploy/claves_y_kms.md`.
