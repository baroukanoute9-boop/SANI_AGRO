#!/usr/bin/env python
import os
import sys

def main():
    # Django va chercher vos configurations dans le dossier 'core'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django n'est pas détecté. Vérifiez que votre environnement virtuel venv est actif."
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
