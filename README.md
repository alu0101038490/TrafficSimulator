# Python OpenStreetMap

## Instalación

1. Siguiendo las recomendaciones de OSMnx (el paquete con el que se dibujan las carreteras) hay que [instalar miniconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html).
2. Seguir las configuraciones recomendadas por el [README de OSMnx](https://github.com/gboeing/osmnx).

    ```shell
    conda config --prepend channels conda-forge
    conda create -n ox --strict-channel-priority osmnx
    ```

3. Activar el entorno llamado *ox* que acabamos de crear para utilizar la versión de Python de dicho entorno.

   ```shell
   conda activate ox
   ```

4. Instalar las librerías que hacen falta (*bs4*, *pyperclip*, *qtmodern* y *pyqt*) con el comando `conda install <pkg>`. Además hay que cambiar la versión del paquete *OSMnx* con el comando `conda install osmnx=0.11.4`.

5. Lo último que hace falta una vez accedamos a los archivos de este repositorio es ejecutar `python POSM/POSM.py`.

