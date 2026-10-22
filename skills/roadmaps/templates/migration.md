# Roadmap: <Project Name>

## Metadata
- Created: <date>
- Goal: Migrate <system> from <source> to <target>
- Status: in_progress

## Steps

### Step 1: Audit current state
- **Type**: linear
- **Status**: pending
- **Next**: Step 2

### Step 2: Plan migration strategy
- **Type**: decision
- **Status**: pending
- **Decision**: Can we migrate in phases?
- **If yes**: Step 3
- **If no**: Step 4

### Step 3: Phase migrations
- **Type**: parallel
- **Status**: pending
- **Sub-steps**: 3a: phase 1, 3b: phase 2, 3c: phase 3
- **Next**: Step 5

### Step 4: Big-bang migration
- **Type**: linear
- **Status**: pending
- **Next**: Step 5

### Step 5: Verify & validate
- **Type**: loop
- **Status**: pending
- **Loop condition**: all integration tests pass
- **Loop back to**: Step 5
- **Next**: Step 6

### Step 6: Cutover
- **Type**: milestone
- **Status**: pending
- **Criteria**: old system decommissioned, all traffic on new system, rollback plan ready
- **Next**: —
