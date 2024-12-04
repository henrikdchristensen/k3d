# Readme
## First run
Assumes kubectl to be installed before running the script.

1. Open Docker Desktop and "Enable integration with additional distros" under Settings/Resources/WSL integration 
2. Open a WSL with Ubuntu.
3. Ensure user have rights to docker: `docker ps`.
    - If not run `sudo usermod -aG docker $USER` and restart WSL.
4. Go to `src/utils/k3d` directory.
5. Ensure file is Unix format `vim run_k3d_and_db.sh -c "set ff=unix" -c ":wq"`.
6. Run file: `./run_k3d_and_db.sh` which will create a k3d cluster and a Yugabyte database.
   It will install k3d and istioctl into the WSL if not already installed.
7. You should now be able to:
    - Access the k3d cluster with `kubectl` (e.g `kubectl get pods -A`).
    - Access the database http://localhost:15433.
    - Access the services e.g. user service http://localhost/user.