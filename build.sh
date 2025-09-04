#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "---> Running build script..."

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply any database migrations
python manage.py migrate

# --- NEW LOGIC: Conditionally populate the database ---
# We will check for an environment variable called POPULATE_DB
# If it's set to "true", we run the scripts.
if [[ $POPULATE_DB == "true" ]]; then
  echo "---> POPULATE_DB is true, running population scripts..."
  python manage.py populate_db --force
  python manage.py populate_fees --force
  echo "---> Database population complete."
fi

echo "---> Build script finished."