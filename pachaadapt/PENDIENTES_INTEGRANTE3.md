# Pendientes del integrante 3 — estado posterior a la fase 2

Este documento resume únicamente las limitaciones que siguen vigentes después de los cambios de la fase 2. Para el alcance, pruebas y archivos modificados, consultar `INFORME_INTEGRANTE3.md` y `RESULTADOS_PRUEBAS_INTEGRANTE3.md` en la raíz.

## Dependencias externas aún pendientes

1. **Proveedor de IA real:** configurar y verificar una URL/modelo y, si corresponde, una credencial legítima. Las pruebas locales no reemplazan la validación con el proveedor del proyecto.
2. **Informes pedagógicos con resultados reales:** el esquema de entregas actualmente guarda respuesta y estado (`submitted`, `reviewed`, `returned`), pero no calificación, rúbrica/resultado de aprendizaje ni una relación institucional validada aula-matrícula. No es correcto derivar calificaciones del texto. El endpoint de informes permanece 503 hasta conectar una fuente autorizada y confirmada.
3. **Autenticación real:** sustituir el mecanismo de cabeceras de demostración por identidad institucional verificada y autorización de grupos. No apto para producción mientras dependa de identidad de demostración.
4. **Sincronización de documentos:** los borradores permanecen en IndexedDB y se guardan explícitamente cuando hay conexión; no existe cola de sincronización de documentos. No se reutiliza ni modifica la cola de entregas.
5. **Verificación de usuario final:** ejecutar prueba visual en navegador, ciclo de desconexión/reconexión real y revisión multi-dispositivo. Las pruebas automatizadas actuales no cubren ese escenario.

## Integraciones implementadas

- El asistente usa preferencias y documentos autorizados del docente.
- La propuesta del asistente se guarda solo tras revisión/acción explícita.
- `MaterialDocumentProcessor` reutiliza el almacenamiento/extracción del integrante 2; la prueba HTTP verificó carga de TXT, importación como documento y rechazo entre propietarios.
- Los módulos del integrante 3 están registrados junto a materiales, adaptaciones, actividades, entregas y sincronización existentes.
- Preferencias, conversaciones y documentos mantienen aislamiento por identidad en pruebas; los permisos siguen dependiendo de la autenticación configurada.

No simular resultados, proveedor, autenticación, matrícula ni sincronización. Revisar `CONFIGURACION_SERVICIOS_IA.md` para la configuración IA y los reportes de entrega para resultados observados.
