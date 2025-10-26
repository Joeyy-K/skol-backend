#!/usr/bin/env bash
# Exit on error
set -o errexit

# --- 1. Install Dependencies ---
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# --- 2. Collect Static Files ---
echo "Collecting static files..."
python manage.py collectstatic --no-input

# --- 3. Apply Database Migrations ---
# This is always required for all environments.
echo "Applying database migrations..."
python manage.py migrate

# --- 4. Populate Database (ONLY IN NON-PRODUCTION ENVIRONMENTS) ---
# This block checks for an environment variable called 'POPULATE_DB'.
# You will only set this variable to "true" on your staging or review servers.
if [ "$POPULATE_DB" = "true" ]; then
  echo "POPULATE_DB is set to true. Populating the database with test data..."
  
  # VVV RUN YOUR SEPARATE SCRIPTS IN THE CORRECT ORDER VVV
  
  # Run the main script first to create users, classes, terms, etc.
  echo "Running main population script (users, academics)..."
  python manage.py populate_db --force
  
  # Run the expenses script
  echo "Running expenses population script..."
  python manage.py populate_expenses
  
  # Run the fees script
  echo "Running financial (fees, invoices, payments) population script..."
  python manage.py populate_fees --force
  
  # Run the events script LAST, as it depends on all other data
  echo "Running calendar events population script..."
  python manage.py populate_events
  
  echo "Database population complete."
else
  echo "POPULATE_DB is not set to true. Skipping database population."
fi

echo "Build finished successfully!"