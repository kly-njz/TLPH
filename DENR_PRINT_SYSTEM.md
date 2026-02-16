# DENR Official Print Styling System

## Overview
Professional print formatting system for DENR (Department of Environment and Natural Resources) Philippines official documents, based on government document standards.

## Features

### 1. Official DENR Header
- **Official Logo**: DENR Philippines seal
- **Republic of the Philippines** banner
- **Department Name**: Properly formatted with official styling
- **Office Information**: Office of the Secretary
- **Contact Details**: Official DENR contact information
- **Border**: 4px solid green (#1b5e20) separator

### 2. Document Sections
- **Document Title**: Large, bold, uppercase with DENR green color
- **Document Number**: Auto-generated reference numbers
- **Date Stamps**: Philippine date format
- **Section Headers**: Numbered (I, II, III, IV) with green underlines

### 3. Data Presentation
- **Statistical Boxes**: Summary statistics with borders
- **Professional Tables**: 
  - Green header row (#1b5e20)
  - Alternating row colors
  - Proper borders and spacing
- **Metadata Sections**: Key-value pairs in highlighted boxes

### 4. Official Elements
- **Signature Section**: 
  - Proper signature line
  - Official title
  - Date field
- **Security Notice**: 
  - Yellow warning box
  - Legal disclaimer
- **Document Reference**: 
  - Barcode-style reference number
  - Generation timestamp
- **Footer**:
  - 3px green top border
  - Complete contact information
  - Official email and website

## Files Included

### 1. Core Stylesheet
**File**: `static/css/denr-print.css`
- Complete @media print styles
- Official DENR color scheme (#1b5e20 - DENR green)
- Typography based on Times New Roman (government standard)
- Section classes (denr-section, denr-official-header, etc.)
- Table styling (denr-table)
- Signature blocks
- Security elements

### 2. Updated Templates

#### Dashboard Report
**File**: `templates/user/dashboard.html`
- Executive summary with statistics
- Application type classification table
- Status analysis table
- Payment status breakdown
- Detailed transaction list
- Official header and footer
- Signature section

#### My Documents / Certificates
**File**: `templates/user/my-documents.html`
- Certificate header with logo
- Certificate title section
- Approval date stamp
- Detailed information table
- Signature section
- Security watermark

#### History Reports
**File**: `templates/user/history.html`
- Applications report with official header
- Service requests report
- Inventory report
- All with proper DENR formatting

### 3. Print Preview
**File**: `templates/denr-print-preview.html`
Demonstration template showing:
- Complete DENR document structure
- All styling elements
- Sample data
- Print button for testing

## Usage

### In Templates
```html
<!-- Add CSS link -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/denr-print.css') }}">

<!-- Use official header -->
<div class="denr-official-header">
  <div class="logo-section">
    <img src="{{ url_for('static', filename='daily-tribune_import_wp-content_uploads_2022_12_DENR.avif') }}" 
         alt="DENR Logo" />
  </div>
  <p class="republic-text">Republic of the Philippines</p>
  <h1 class="department-name">Department of Environment and Natural Resources</h1>
  <p class="office-name">Office of the Secretary</p>
  <p class="address">DENR Building, Visayas Avenue...</p>
</div>

<!-- Document title -->
<div class="denr-doc-title">
  <h1>YOUR DOCUMENT TITLE</h1>
  <p class="subtitle">Subtitle here</p>
  <p class="doc-number">Document No. XXX-12345678</p>
</div>

<!-- Sections -->
<div class="denr-section">
  <h2>I. SECTION TITLE</h2>
  <p>Content here...</p>
</div>

<!-- Tables -->
<table class="denr-table">
  <thead>
    <tr>
      <th>Column 1</th>
      <th>Column 2</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Data 1</td>
      <td>Data 2</td>
    </tr>
  </tbody>
</table>

<!-- Signature -->
<div class="denr-signature-section">
  <div class="denr-signature-block">
    <div class="signature-line"></div>
    <p class="signatory-name">Official Name</p>
    <p class="signatory-title">Position</p>
  </div>
</div>

<!-- Security notice -->
<div class="denr-security-notice">
  <p><strong>NOTICE:</strong> This is an electronically generated document...</p>
</div>
```

### In JavaScript (PDF Generation)
```javascript
// Create container
const pdfContainer = document.createElement('div');
pdfContainer.style.fontFamily = "'Times New Roman', Georgia, serif";
pdfContainer.style.lineHeight = '1.6';

// Add header
const header = document.createElement('div');
header.className = 'denr-official-header';
header.innerHTML = `
  <img src="${logoUrl}" alt="DENR Logo" style="width: 80px; height: 80px;" />
  <p style="font-size: 11pt;">Republic of the Philippines</p>
  <h1 style="font-size: 13pt; color: #1b5e20;">Department of Environment and Natural Resources</h1>
  ...
`;

// Add sections
const section = document.createElement('div');
section.className = 'denr-section';
section.innerHTML = `
  <h2 style="color: #1b5e20; border-bottom: 2px solid #1b5e20;">
    I. SECTION TITLE
  </h2>
  <p>Content...</p>
`;
```

## Color Scheme (Official DENR Colors)

```css
/* Primary DENR Green */
#1b5e20 - Main color for headers, borders, text emphasis

/* Secondary Greens */
#2e7d32 - Approved status, positive indicators
#558b2f - Alternative green for variety
#f1f8e9 - Light green background for boxes

/* Status Colors */
#1b5e20 - Approved (green)
#f57c00 - Pending (orange)
#c62828 - Rejected/Error (red)

/* Warning/Notice */
#ffc107 - Warning border
#fff3cd - Warning background
#856404 - Warning text
```

## Typography

```css
/* Official Government Font */
font-family: 'Times New Roman', 'Georgia', serif;

/* Sizes */
18pt - Document titles
13pt - Section headers (H2)
11pt - Department name
10pt - Body text, metadata
9pt  - Small text, footnotes
8pt  - Footer text
```

## Page Setup

```css
@page {
  size: A4;           /* Standard government document size */
  margin: 20mm 15mm;  /* Official margins */
}
```

## Print Classes

| Class | Purpose |
|-------|---------|
| `.denr-official-header` | Top section with logo and department info |
| `.denr-doc-title` | Document title section |
| `.denr-section` | Content sections with headers |
| `.denr-table` | Styled tables with green headers |
| `.denr-stat-box` | Statistical summary boxes |
| `.denr-metadata` | Key-value information boxes |
| `.denr-signature-section` | Signature area |
| `.denr-signature-block` | Individual signature block |
| `.denr-security-notice` | Warning/security notices |
| `.denr-doc-reference` | Document reference/barcode area |
| `.status-approved` | Green approved status |
| `.status-pending` | Orange pending status |
| `.status-rejected` | Red rejected status |
| `.no-print` | Hidden when printing |
| `.avoid-break` | Prevent page breaks inside |
| `.page-break` | Force page break after |

## Testing

### View Print Preview
1. Open browser
2. Navigate to `/denr-print-preview` (if route added) or open the template
3. Click "Print Document" button
4. Use browser's Print Preview to see result

### Generate PDF
Any page with the print styles will automatically use them when:
- Clicking print buttons
- Using `window.print()`
- Generating PDFs with html2pdf.js

## Reference
Based on official DENR Philippines Annual Report format:
https://denr.gov.ph/wp-content/uploads/2024/02/DENR-Annual-Report-for-FY2021.pdf

## Implementation Checklist

- [x] Create denr-print.css stylesheet
- [x] Update dashboard.html with official styling
- [x] Update my-documents.html certificates
- [x] Update history.html reports
- [x] Add DENR logo to all print headers
- [x] Implement signature sections
- [x] Add security notices
- [x] Create print preview template
- [x] Document usage and classes

## Maintenance

### Updating Logo
Replace file: `static/daily-tribune_import_wp-content_uploads_2022_12_DENR.avif`
Or update path in templates to new logo location.

### Updating Contact Info
Edit in each template's header section:
- Address
- Phone numbers
- Email
- Website

### Adding New Report Types
1. Copy header structure from existing templates
2. Use `.denr-section` for content areas
3. Use `.denr-table` for data tables
4. Add signature section at bottom
5. Include security notice
6. Add footer with contact info

## Browser Compatibility
- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Print to PDF: Tested with html2pdf.js

## Notes
- Logo is included using Flask's `url_for()` - ensure static files are accessible
- All measurements use print standards (pt, mm)
- Colors match official DENR branding
- Typography follows Philippine government document standards
