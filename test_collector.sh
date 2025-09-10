#!/bin/bash
# Test Claude collector
export SAYU_DEBUG=1
export RUST_BACKTRACE=1

# Create a simple test message file
cat > /tmp/test_msg.txt << 'EOF'
test: verify Claude collector timestamp parsing
EOF

# Run the commit-msg hook directly
./target/release/sayu hook commit-msg /tmp/test_msg.txt

echo "---"
echo "Test message after hook:"
cat /tmp/test_msg.txt