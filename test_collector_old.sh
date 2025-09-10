#!/bin/bash
# Test with older timestamp to get more events
export SAYU_DEBUG=1

# Get timestamp from 1 hour ago
OLD_TS=$(($(date +%s) - 3600))

# Create test script
cat > /tmp/test_claude.sh << 'SCRIPT'
#!/bin/bash
# Temporarily override git log to return older timestamp
if [[ "$1" == "log" && "$2" == "-1" && "$3" == "--format=%ct" ]]; then
    echo "TIMESTAMP_PLACEHOLDER"
else
    /usr/bin/git "$@"
fi
SCRIPT

sed -i '' "s/TIMESTAMP_PLACEHOLDER/$OLD_TS/" /tmp/test_claude.sh
chmod +x /tmp/test_claude.sh

# Run with PATH override
PATH="/tmp:$PATH" ./target/release/sayu hook commit-msg /tmp/test_msg.txt

echo "---"
echo "Test message after hook:"
cat /tmp/test_msg.txt
