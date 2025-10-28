# Contact Import Guide

## 📋 Importing Your Existing Contact List

You have a **pre-purchased contact list** that you want to match to your TTB brands. This guide shows you how to import them **without using Apollo API credits**.

---

## 🎯 **Benefits of Importing Existing Contacts**

✅ **Save Apollo Credits** - No API calls needed for brands you already have contacts for
✅ **Instant Enrichment** - Populate brands immediately
✅ **Better ROI** - Use Apollo only for brands you DON'T have contacts for
✅ **Data Consolidation** - All contacts in one system

---

## 📊 **How the Contact Hierarchy Works**

### **3-Tier Contact Discovery System**

```
┌─────────────────────────────────────────────┐
│ TIER 1: Pre-Purchased Contact List         │
│ (Your existing paid contacts - FREE!)      │
├─────────────────────────────────────────────┤
│ TIER 2: Apollo Auto-Enrich                 │
│ (Brands with websites - 1 credit/contact)  │
├─────────────────────────────────────────────┤
│ TIER 3: Apollo Manual Search               │
│ (Brands without websites - needs approval) │
└─────────────────────────────────────────────┘
```

**Priority Order:**
1. Check if brand has imported contacts → Use those (FREE)
2. If no contacts, check if brand has website → Apollo auto-enrich
3. If no website → Apollo manual search with approval

---

## 🚀 **Quick Start: Import Your Contacts**

### **Step 1: Prepare Your CSV File**

Your CSV should have these columns (names can vary):

**Required:**
- `brand_name` or `company_name` - Must match TTB brand names
- `contact_name` or `full_name` - Contact's full name
- `email` - Contact email address
- `title` or `job_title` - Job title

**Optional (Recommended):**
- `linkedin` or `linkedin_url` - LinkedIn profile
- `department` - Department/division
- `seniority` - Seniority level
- `website` or `domain` - Company website

**Example CSV format:**
```csv
brand_name,contact_name,email,title,linkedin
CHATEAU EXAMPLE,John Smith,john@example.com,CEO,https://linkedin.com/in/johnsmith
CHATEAU EXAMPLE,Jane Doe,jane@example.com,VP Sales,https://linkedin.com/in/janedoe
ANOTHER BRAND,Bob Wilson,bob@anotherbrand.com,Owner,
```

---

### **Step 2: Run the Import Script**

```bash
# Basic usage (auto-detect columns)
python import_existing_contacts.py your_contacts.csv

# With custom database path
python import_existing_contacts.py your_contacts.csv --db data/brands.db
```

---

### **Step 3: Review Results**

The script will show:
- ✅ **Matched brands** - Contacts successfully imported
- ❌ **Unmatched brands** - Brand names that didn't match (needs manual review)
- 📊 **Summary stats** - Total contacts imported

**Example output:**
```
============================================================
📊 IMPORT SUMMARY
============================================================
Total Contacts in CSV: 150
Matched Brands: 45
Unmatched Brands: 5
Contacts Saved: 142

✅ Updated Brands (45):
  - CHATEAU EXAMPLE
  - DOMAINE ANOTHER
  - WINE PRODUCER LLC
  ... and 42 more

❌ Unmatched Brand Names (5):
  - EXAMPLE WINES (possible typo)
  - ANOTHER CO (not in database)
  ... and 3 more
============================================================
```

---

## 🔧 **Advanced: Custom Column Mapping**

If your CSV has different column names, edit the script's `column_mapping`:

```python
# Edit import_existing_contacts.py line ~250
column_mapping = {
    'Company': 'brand_name',           # Your CSV has "Company"
    'Full Name': 'contact_name',       # Your CSV has "Full Name"
    'Work Email': 'email',             # Your CSV has "Work Email"
    'Job Title': 'title',              # Your CSV has "Job Title"
    'LinkedIn Profile': 'linkedin_url' # Your CSV has "LinkedIn Profile"
}

stats = importer.import_contacts_csv(args.csv_file, mapping=column_mapping)
```

---

## 🎯 **How Matching Works**

### **Brand Name Matching Algorithm:**

1. **Exact Match (100% confidence):**
   - `CHATEAU EXAMPLE` in CSV → `CHATEAU EXAMPLE` in database ✅

2. **Fuzzy Match (80%+ similarity):**
   - `Chateau Example Wines` → `CHATEAU EXAMPLE` (85% match) ✅
   - `Example Estate` → `CHATEAU EXAMPLE` (only 50% match) ❌

3. **Contains Match:**
   - `EXAMPLE` in CSV → `CHATEAU EXAMPLE WINES` in database ✅

**Unmatched brands** are logged so you can manually review and adjust.

---

## 📊 **Contact Relevance Scoring**

All imported contacts are automatically scored for Helmsman Imports outreach:

| Title Keywords | Score | Decision Maker |
|---------------|-------|----------------|
| Owner, Founder, CEO, President | 100 | ✅ Yes |
| VP, Vice President | 90 | ✅ Yes |
| Director | 85 | ✅ Yes |
| Import/Export Manager | 80 | ✅ Yes |
| Sales Manager | 70 | No |
| Other | 50 | No |

---

## 🔄 **Workflow: Combining Imported + Apollo Contacts**

### **Scenario 1: Brand has imported contacts**
```
1. Check database → Find imported contacts
2. Display contacts on brand page
3. Skip Apollo enrichment (already have contacts)
4. Save credits for other brands
```

### **Scenario 2: Brand has NO imported contacts + has website**
```
1. Check database → No contacts found
2. Trigger Apollo auto-enrich by domain
3. Save Apollo contacts to database
4. Use ~10 credits
```

### **Scenario 3: Brand has partial imported contacts**
```
1. Show imported contacts first
2. Option to "Find More Contacts" via Apollo
3. User decides if worth spending credits
```

---

## 💡 **Best Practices**

### **Before Import:**
- ✅ Clean your CSV (remove duplicates)
- ✅ Standardize brand names to match TTB format
- ✅ Verify email addresses are valid
- ✅ Check for encoding issues (UTF-8 recommended)

### **After Import:**
- ✅ Review unmatched brands
- ✅ Manually map mismatches
- ✅ Re-run import with corrected brand names
- ✅ Use Apollo only for brands with no imported contacts

### **Credit Optimization:**
```
Total Brands: 202 with websites
Imported Contacts: 50 brands (FREE)
Remaining for Apollo: 152 brands
Apollo Budget: 500 credits/month
Enrichment Rate: 152 ÷ 500 = ~30 brands/month (5 contacts each)
Time to Complete: ~5 months
```

**With imported contacts, you save ~5 months of waiting!**

---

## 🐛 **Troubleshooting**

### **"Required columns not found"**
- Check your CSV column names
- Use custom column mapping (see Advanced section)

### **"No match found for: BRAND NAME"**
- Brand name in CSV doesn't match database
- Check for typos, extra spaces, capitalization
- Try fuzzy matching by cleaning brand name

### **"Error saving contacts for BRAND"**
- Database permissions issue
- Check database path is correct
- Ensure brands table has apollo_data column

---

## 🎯 **Next Steps**

After importing your existing contacts:

1. **Verify import** - Check brand detail pages show contacts
2. **Identify gaps** - Find brands with no contacts
3. **Prioritize Apollo enrichment** - Use credits on high-value brands only
4. **Track ROI** - Monitor which contact source performs best

---

## 📞 **Support**

If you need help:
- Check column names match expected format
- Review unmatched brands list
- Manually fix brand name mismatches
- Re-run import for corrected entries

**The import script is safe** - it only adds data, never deletes existing contacts!
