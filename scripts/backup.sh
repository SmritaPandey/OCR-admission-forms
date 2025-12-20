#!/bin/bash
# Database and Files Backup Script

set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

echo "=========================================="
echo "Backup Script - $(date)"
echo "=========================================="
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Database backup
echo "📦 Backing up database..."
if docker-compose exec -T postgres pg_dump -U student_admin admission_forms | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"; then
    echo "   ✅ Database backup created: db_$DATE.sql.gz"
    DB_SIZE=$(du -h "$BACKUP_DIR/db_$DATE.sql.gz" | cut -f1)
    echo "   📊 Size: $DB_SIZE"
else
    echo "   ❌ Database backup failed"
    exit 1
fi

# Uploads backup
echo "📁 Backing up uploads..."
if docker-compose exec -T backend tar -czf - /app/uploads 2>/dev/null | cat > "$BACKUP_DIR/uploads_$DATE.tar.gz"; then
    echo "   ✅ Uploads backup created: uploads_$DATE.tar.gz"
    UPLOADS_SIZE=$(du -h "$BACKUP_DIR/uploads_$DATE.tar.gz" | cut -f1)
    echo "   📊 Size: $UPLOADS_SIZE"
else
    echo "   ⚠️  Uploads backup skipped (may be empty)"
fi

# Training data backup
echo "🎓 Backing up training data..."
if docker-compose exec -T backend tar -czf - /app/training_data 2>/dev/null | cat > "$BACKUP_DIR/training_data_$DATE.tar.gz"; then
    echo "   ✅ Training data backup created: training_data_$DATE.tar.gz"
    TRAINING_SIZE=$(du -h "$BACKUP_DIR/training_data_$DATE.tar.gz" | cut -f1)
    echo "   📊 Size: $TRAINING_SIZE"
else
    echo "   ⚠️  Training data backup skipped (may be empty)"
fi

# Models backup
echo "🤖 Backing up models..."
if docker-compose exec -T backend tar -czf - /app/models 2>/dev/null | cat > "$BACKUP_DIR/models_$DATE.tar.gz"; then
    echo "   ✅ Models backup created: models_$DATE.tar.gz"
    MODELS_SIZE=$(du -h "$BACKUP_DIR/models_$DATE.tar.gz" | cut -f1)
    echo "   📊 Size: $MODELS_SIZE"
else
    echo "   ⚠️  Models backup skipped (may be empty)"
fi

# Cleanup old backups
echo ""
echo "🧹 Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "*.gz" -type f -mtime +$RETENTION_DAYS -delete
echo "   ✅ Cleanup complete"

# Summary
echo ""
echo "=========================================="
echo "✅ Backup Complete!"
echo "=========================================="
echo ""
echo "Backup location: $BACKUP_DIR"
echo "Total backups: $(ls -1 "$BACKUP_DIR"/*.gz 2>/dev/null | wc -l)"
echo "Total size: $(du -sh "$BACKUP_DIR" | cut -f1)"
echo ""
