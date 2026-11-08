#!/usr/bin/env bash
# Script de compilación para Render. Se detiene ante el primer error.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Usuarios y platos de demostración solo si SEED_DEMO=1.
# Ojo: seed_data restablece las contraseñas demo cada vez que se ejecuta.
if [ "${SEED_DEMO:-0}" = "1" ]; then
  python manage.py seed_data
fi

# El disco de Render se borra en cada despliegue: restaura las fotos de los platos demo.
python manage.py presentar_menu
