#!/bin/bash
# Database and Files Restore Script

set -e

BACKUP_DIR="/backups"

echo "=========================================="
echo "Restore Script"
echo "=========================================="
echo ""

# List available backups
echo "📋 Available backups:"
ls -lh "$BACKUP_DIR"/*.gz 2>/dev/null | awk '{print $9, "(" $5 ")"}' || {
    echo "   No backups found in $BACKUP_DIR"
    exit 1
}

echo ""
read -p "Enter backup date (YYYYMMDD_HHMMSS) or 'latest': " BACKUP_DATE

if [ "$BACKUP_DATE" = "latest" ]; then
    DB_BACKUP=$(ls -t "$BACKUP_DIR"/db_*.sql.gz | head -1)
    UPLOADS_BACKUP=$(ls -t "$BACKUP_DIR"/uploads_*.tar.gz | head -1)
    TRAINING_BACKUP=$(ls -t "$BACKUP_DIR"/training_data_*.tar.gz | head -1)
    MODELS_BACKUP=$(ls -t "$BACKUP_DIR"/models_*.tar.gz | head -1)
else
    DB_BACKUP="$BACKUP_DIR/db_${BACKUP_DATE}.sql.gz"
    UPLOADS_BACKUP="$BACKUP_DIR/uploads_${BACKUP_DATE}.tar.gz"
    TRAINING_BACKUP="$BACKUP_DIR/training_data_${BACKUP_DATE}.tar.gz"
    MODELS_BACKUP="$BACKUP_DIR/models_${BACKUP_DATE}.tar.gz"
fi

# Confirm restore
echo ""
echo "⚠️  WARNING: This will overwrite existing data!"
echo "   Database backup: $DB_BACKUP"
read -p "Continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Restore database
if [ -f "$DB_BACKUP" ]; then
    echo ""
    echo "📦 Restoring database..."
    gunzip -c "$DB_BACKUP" | docker-compose exec -T postgres psql -U student_admin -d admission_forms
    echo "   ✅ Database restored"
else
    echo "   ⚠️  Database backup not found: $DB_BACKUP"
fi

# Restore uploads
if [ -f "$UPLOADS_BACKUP" ]; then
    echo "📁 Restoring uploads..."
    cat "$UPLOADS_BACKUP" | docker-compose exec -T backend tar -xzf - -C /
    echo "   ✅ Uploads restored"
else
    echo "   ⚠️  Uploads backup not found"
fi

# Restore training data
if [ -f "$TRAINING_BACKUP" ]; then
    echo "🎓 Restoring training data..."
    cat "$TRAINING_BACKUP" | docker-compose exec -T backend tar -xzf - -C /
    echo "   ✅ Training data restored"
else
    echo "   ⚠️  Training data backup not found"
fi

# Restore models
if [ -f "$MODELS_BACKUP" ]; then
    echo "🤖 Restoring models..."
    cat "$MODELS_BACKUP" | docker-compose exec -T backend tar -xzf - -C /
    echo "   ✅ Models restored"
else
    echo "   ⚠️  Models backup not found"
fi

echo ""
echo "=========================================="
echo "✅ Restore Complete!"
echo "=========================================="
echo ""
