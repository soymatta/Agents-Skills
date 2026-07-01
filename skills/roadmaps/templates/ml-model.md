# Roadmap: <Project Name>

## Metadata
- Created: <date>
- Goal: Train a <model_type> with ><N>% accuracy
- Status: in_progress

## Steps

### Step 1: Prepare data
- **Type**: linear
- **Status**: pending
- **Next**: Step 2

### Step 2: Train baseline
- **Type**: linear
- **Status**: pending
- **Next**: Step 3

### Step 3: Evaluate
- **Type**: decision
- **Status**: pending
- **Decision**: Metric >= target?
- **If yes**: Step 5
- **If no**: Step 4

### Step 4: Optimize
- **Type**: loop
- **Status**: pending
- **Loop condition**: metric improves >1% per iteration, max 10 runs
- **Loop back to**: Step 3
- **Next**: Step 3

### Step 5: Export & ship
- **Type**: milestone
- **Status**: pending
- **Criteria**: model saved, pipeline documented, API ready
- **Next**: —
