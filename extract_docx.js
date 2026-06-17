const mammoth = require('mammoth');
const fs = require('fs');
const path = require('path');

const dataDir = path.join(__dirname, 'India_runs_data_and_ai_challenge');
const files = ['README.docx', 'job_description.docx', 'redrob_signals_doc.docx', 'submission_spec.docx'];

async function extract() {
  for (const file of files) {
    const filePath = path.join(dataDir, file);
    try {
      const result = await mammoth.extractRawText({ path: filePath });
      const outPath = path.join(dataDir, file.replace('.docx', '.txt'));
      fs.writeFileSync(outPath, result.value);
      console.log(`Extracted: ${file} -> ${result.value.length} chars`);
    } catch(e) {
      console.error(`Error with ${file}: ${e.message}`);
    }
  }
}

extract();
