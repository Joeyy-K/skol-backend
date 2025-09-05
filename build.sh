#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "---> Running build script..."

# Install dependencies
pip install -r requirements.txt

# Create static directory if it doesn't exist
mkdir -p static

# Collect static files
python manage.py collectstatic --no-input

# Apply any database migrations
python manage.py migrate

# --- NEW LOGIC: Conditionally populate the database ---
# We will check for an environment variable called POPULATE_DB
# If it's set to "true", we run the scripts.
if [[ $POPULATE_DB == "true" ]]; then
    echo "---> POPULATE_DB is true, running population scripts..."
    echo "---> Populating main database..."
    python manage.py populate_db --force
    
    # Check if populate_fees command exists before running
    if python manage.py help | grep -q "populate_fees"; then
        echo "---> Populating fees database..."
        python manage.py populate_fees --force
    else
        echo "---> populate_fees command not found, skipping..."
    fi
    
    echo "---> Database population complete."
else
    echo "---> POPULATE_DB not set to 'true', skipping database population."
fi

echo "---> Build script finished."