# Migration Guide: Enhanced Resume Analysis

## Overview

This guide provides step-by-step instructions for migrating existing deployments to use the enhanced resume analysis feature. The migration is additive and non-breaking - existing sessions will continue to work with basic analysis.

## Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Virtual environment access
- Database backup (recommended)

## Migration Steps

### Step 1: Database Migration

Run the migration script to add enhanced analysis columns:

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Run migration
python scripts/migrate_enhanced_analysis.py
```

**What the migration does:**
1. Adds `enhanced_analysis` column (JSONB) to `practice_sessions` table
2. Adds `custom_additions` column (TEXT) to `practice_sessions` table
3. Adds `improved_pdf_url` column (VARCHAR(500)) to `practice_sessions` table
4. Creates indexes for efficient querying

**Migration verification:**
```sql
-- Check new columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'practice_sessions' 
AND column_name IN ('enhanced_analysis', 'custom_additions', 'improved_pdf_url');
```

### Step 2: Backend Deployment

The following backend changes are required:

#### 1. Enhanced Analyzer Service

The `services/enhanced_analyzer.py` module is now integrated into the pipeline. This module:

- Wraps `analyzer.py` functions for async integration
- Provides `analyze_resume_enhanced()` for enhanced analysis
- Provides `refine_custom_additions()` for gap refinement
- Provides `generate_ats_pdf()` for PDF generation

**No additional installation required** - the module uses existing dependencies.

#### 2. Orchestrator Updates

The `services/orchestrator.py` module now calls enhanced analysis after basic parsing:

```python
# After resume parsing, run enhanced analysis
enhanced_results = await analyze_resume_enhanced(
    resume_text=resume_text,
    jd_text=job_description,
)
```

**Changes made:**
- Enhanced analysis runs automatically for new sessions
- Falls back to basic analysis if enhanced fails
- Stores results in database for future use

#### 3. API Endpoints

New endpoints are available in `api/routers/practice.py`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/practice/session/{session_id}/refine` | POST | Refine custom additions and gaps |
| `/practice/session/{session_id}/pdf` | GET | Generate ATS-optimized PDF |

Updated endpoints:
- `GET /practice/session/{session_id}` - Now includes `enhanced_analysis` field
- `POST /practice/initialize` - Now triggers enhanced analysis automatically

### Step 3: Frontend Integration

#### 1. ResumeReport Component

Create `frontend/components/ResumeReport.tsx` to display enhanced analysis:

**Key features:**
- Display ATS score and match score
- Show gaps with actionable items
- Display improvements as suggestions
- Show core strengths
- Display summary

#### 2. CustomAdditionsForm Component

Create `frontend/components/CustomAdditionsForm.tsx` to allow custom additions:

**Key features:**
- Text area for custom additions
- Categorize by section (certificates, education, additional)
- Submit handler to call refine endpoint
- Display refined content

#### 3. Assessment Page Updates

Update `frontend/app/practice/[session_id]/assessment/page.tsx`:

**Changes:**
- Display enhanced report when available
- Add PDF download button
- Handle loading states for PDF generation
- Show custom additions form

#### 4. API Client Updates

Update `frontend/lib/api.ts`:

```typescript
// Add new functions
export async function refineCustomAdditions(
  sessionId: string,
  customAdditions: string,
  gapSelections?: Record<string, string>
): Promise<RefineResponse> {
  const response = await fetch(`/api/practice/session/${sessionId}/refine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ custom_additions: customAdditions, gap_selections: gapSelections }),
  });
  return response.json();
}

export async function generatePDF(sessionId: string, template?: string): Promise<Blob> {
  const url = `/api/practice/session/${sessionId}/pdf`;
  const response = await fetch(template ? `${url}?template=${template}` : url);
  return response.blob();
}
```

## Testing the Migration

### Test 1: New Session with Enhanced Analysis

1. Create a new practice session
2. Upload a resume and provide job description
3. Verify enhanced analysis runs automatically
4. Check that `enhanced_analysis` field is populated in database

### Test 2: Refine Custom Additions

1. Navigate to assessment page
2. Enter custom additions in the form
3. Submit and verify refined content
4. Check database for updated `custom_additions` and `enhanced_analysis`

### Test 3: PDF Generation

1. Click "Download Improved Resume" button
2. Verify PDF is generated with enhanced content
3. Test different templates (Classic ATS, Modern Accent, Two-Column Professional)
4. Verify PDF contains all sections correctly

### Test 4: Backward Compatibility

1. Create a session without enhanced analysis
2. Verify basic analysis still works
3. Verify `enhanced_analysis` field is `null`
4. Verify session can proceed to interview

## Rollback Plan

If issues occur, rollback is straightforward:

### Code Rollback

1. Revert code changes to previous version
2. Restart backend services
3. Existing sessions will continue to work with basic analysis

### Database Rollback

The migration is additive only - no data loss. To remove new columns:

```sql
-- Only if absolutely necessary
ALTER TABLE practice_sessions DROP COLUMN IF EXISTS enhanced_analysis;
ALTER TABLE practice_sessions DROP COLUMN IF EXISTS custom_additions;
ALTER TABLE practice_sessions DROP COLUMN IF EXISTS improved_pdf_url;
```

**Note:** This will lose any enhanced analysis data but basic analysis will remain intact.

## Monitoring and Validation

### Health Checks

1. **Database:** Verify new columns exist
2. **API:** Test new endpoints with curl
3. **Frontend:** Verify assessment page displays enhanced data

### Logging

Monitor for these log messages:

```bash
# Successful enhanced analysis
INFO: Enhanced analysis completed for session {session_id}

# Fallback to basic analysis
WARNING: Enhanced analysis failed for session {session_id}, using basic analysis

# PDF generation
INFO: PDF generated for session {session_id} with template {template_name}
```

### Error Handling

Common issues and solutions:

| Error | Solution |
|-------|----------|
| `reportlab` not found | `pip install reportlab` |
| LLM API errors | Check API key and quota |
| Database errors | Verify migration ran successfully |
| Frontend errors | Check API client functions |

## Performance Considerations

### Enhanced Analysis

- Runs in background task (non-blocking)
- Uses LLM API calls (2-5 seconds typical)
- Falls back to basic analysis if slow

### PDF Generation

- Runs on-demand (user-triggered)
- May take 5-15 seconds for complex resumes
- Consider adding progress indicator

### Database

- New columns are JSONB/TEXT (efficient storage)
- No performance impact on existing queries
- Indexes created for common queries

## Support

For issues or questions:

1. Check logs for error messages
2. Verify database migration completed
3. Test with sample resume
4. Contact development team with session_id

## FAQ

**Q: Will existing sessions be affected?**
A: No. Existing sessions will continue to work with basic analysis. Enhanced analysis only runs for new sessions.

**Q: Can I re-run enhanced analysis on existing sessions?**
A: Yes. Use the refine endpoint to trigger enhanced analysis on demand.

**Q: What happens if LLM API fails?**
A: System falls back to basic analysis automatically. Session can proceed to interview.

**Q: Do I need to update the frontend?**
A: Yes. Frontend updates are required to display enhanced analysis and enable PDF generation.

**Q: Can I customize the scoring weights?**
A: Yes. Modify `services/enhanced_analyzer.py` to adjust scoring guidelines.
