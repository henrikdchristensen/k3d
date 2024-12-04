# Readme
## First run
1. Open Docker Desktop and "Enable integration with additional distros" under Settings/Resources/WSL integration 
2. Open a WSL with Ubuntu.
3. Ensure user have rights to docker: `docker ps`.
    - If not run `sudo usermod -aG docker $USER` and restart WSL.
4. Go to `src/utils/database` directory.
5. Ensure file is Unix format `vim run_local_yugabyte.sh -c "set ff=unix" -c ":wq"`.
6. Run file: `./run_local_yugabyte.sh` which will create a Yugabyte database.
7. You should now be able to access the database http://localhost:15433.