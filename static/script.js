document.addEventListener('DOMContentLoaded', () => {
    // Elements on Workspace page
    const fileInput = document.getElementById('audio-upload');
    const dropZone = document.getElementById('drop-zone');
    const filePreviewCard = document.getElementById('file-preview-card');
    const previewFileName = document.getElementById('preview-file-name');
    const previewFileSize = document.getElementById('preview-file-size');
    const removeFileBtn = document.getElementById('remove-file-btn');
    const dropZoneIcon = document.querySelector('.drop-zone-icon');
    const dropZoneText = document.querySelector('.drop-zone-text');

    const uploadForm = document.getElementById('upload-form');
    const transcribeBtn = document.getElementById('transcribe-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');
    const errorBanner = document.getElementById('error-message');

    const loadingState = document.getElementById('loading-state');
    const resultsSection = document.getElementById('results-section');

    const rawTranscriptBox = document.getElementById('raw-transcript-box');
    const overallSummaryText = document.getElementById('overall-summary-text');
    const summaryLangBadge = document.getElementById('summary-lang-badge');
    const personwiseContainer = document.getElementById('personwise-container');
    const actionItemsContainer = document.getElementById('action-items-container');

    const copyReportBtn = document.getElementById('copy-report-btn');
    const copyTranscriptBtn = document.getElementById('copy-transcript-btn');
    const exportTxtBtn = document.getElementById('export-txt-btn');
    const exportMdBtn = document.getElementById('export-md-btn');
    const newRecordingBtn = document.getElementById('new-recording-btn');

    let currentData = null;

    if (!uploadForm) return;

    // Drag & Drop Handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            handleSelectedFile(files[0]);
        }
    });

    dropZone.addEventListener('click', (e) => {
        if (e.target.closest('#remove-file-btn')) return;
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleSelectedFile(e.target.files[0]);
        }
    });

    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function handleSelectedFile(file) {
        if (file.size > 50 * 1024 * 1024) {
            showError("File size exceeds 50MB limit. Please upload a smaller audio recording.");
            return;
        }

        hideError();
        previewFileName.textContent = file.name;
        previewFileSize.textContent = formatBytes(file.size);

        if (dropZoneIcon) dropZoneIcon.classList.add('hidden');
        if (dropZoneText) dropZoneText.classList.add('hidden');
        filePreviewCard.classList.remove('hidden');

        transcribeBtn.disabled = false;
    }

    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            resetFileInput();
        });
    }

    function resetFileInput() {
        fileInput.value = '';
        if (dropZoneIcon) dropZoneIcon.classList.remove('hidden');
        if (dropZoneText) dropZoneText.classList.remove('hidden');
        filePreviewCard.classList.add('hidden');
        transcribeBtn.disabled = true;
    }

    function showError(message) {
        errorBanner.textContent = message;
        errorBanner.classList.remove('hidden');
    }

    function hideError() {
        errorBanner.textContent = '';
        errorBanner.classList.add('hidden');
    }

    // Handle Form Submit
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!fileInput.files || fileInput.files.length === 0) {
            showError("Please select an audio file to transcribe.");
            return;
        }

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        hideError();
        resultsSection.classList.add('hidden');
        loadingState.classList.remove('hidden');
        transcribeBtn.disabled = true;
        btnText.textContent = "Processing Recording...";
        btnSpinner.classList.remove('hidden');

        loadingState.scrollIntoView({ behavior: 'smooth' });

        try {
            const response = await fetch('/api/transcribe', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Failed to process audio recording.");
            }

            currentData = data;
            renderResults(data);

            loadingState.classList.add('hidden');
            resultsSection.classList.remove('hidden');
            resultsSection.scrollIntoView({ behavior: 'smooth' });

        } catch (err) {
            console.error(err);
            loadingState.classList.add('hidden');
            showError(err.message || "An unexpected error occurred during transcription.");
        } finally {
            transcribeBtn.disabled = false;
            btnText.textContent = "Transcribe & Analyze Meeting";
            btnSpinner.classList.add('hidden');
        }
    });

    function renderResults(data) {
        // 1. PLACED FIRST: Verbatim Transcription
        rawTranscriptBox.textContent = data.raw_transcript || "Transcript unavailable.";

        // 2. PLACED SECOND: Overall Meeting Summary (Tanglish if bilingual, English if English)
        overallSummaryText.textContent = data.overall_summary || "No overall summary available for this recording.";
        if (summaryLangBadge) {
            if (data.is_bilingual) {
                summaryLangBadge.textContent = "Tanglish Summary (Bilingual Input)";
                summaryLangBadge.className = "badge-lang-pill badge-tanglish";
            } else {
                summaryLangBadge.textContent = "English Executive Summary";
                summaryLangBadge.className = "badge-lang-pill badge-english";
            }
        }

        // 3. PLACED THIRD: Person-wise Summary
        personwiseContainer.innerHTML = '';
        const personwise = data.personwise_summary || [];
        if (personwise.length > 0) {
            personwise.forEach((item) => {
                const spkName = item.speaker || "Speaker";
                const avatarLetter = spkName.replace("Speaker ", "").charAt(0) || "P";
                const card = document.createElement('div');
                card.className = 'speaker-card';
                card.innerHTML = `
                    <div class="speaker-card-header">
                        <div class="speaker-avatar">${escapeHtml(avatarLetter)}</div>
                        <span class="speaker-name">${escapeHtml(spkName)}</span>
                    </div>
                    <p class="speaker-text">${escapeHtml(item.summary || item.text || "No remarks noted.")}</p>
                `;
                personwiseContainer.appendChild(card);
            });
        } else {
            personwiseContainer.innerHTML = '<p class="speaker-text">No person-wise breakdown available.</p>';
        }

        // 4. PLACED FOURTH: Actions To Be Done (Who said & Who assigned to)
        actionItemsContainer.innerHTML = '';
        const actions = data.action_items || [];
        if (actions.length > 0) {
            actions.forEach((act) => {
                const task = act.task || (typeof act === 'string' ? act : 'Action item');
                const raisedBy = act.raised_by || 'Meeting Lead';
                const assignedTo = act.assigned_to || 'Assigned Owner';

                const card = document.createElement('div');
                card.className = 'action-item-card';
                card.innerHTML = `
                    <div class="action-card-top">
                        <input type="checkbox" class="action-checkbox">
                        <span class="action-task-text">${escapeHtml(task)}</span>
                    </div>
                    <div class="action-badges-row">
                        <div class="badge-role badge-raised">
                            <span class="badge-label">Raised by:</span>
                            <span class="badge-val">${escapeHtml(raisedBy)}</span>
                        </div>
                        <div class="badge-role badge-assigned">
                            <span class="badge-label">Assigned to:</span>
                            <span class="badge-val">${escapeHtml(assignedTo)}</span>
                        </div>
                    </div>
                `;
                actionItemsContainer.appendChild(card);
            });
        } else {
            actionItemsContainer.innerHTML = `
                <div class="no-actions-box">
                    <p>No explicit action items were mentioned in this meeting recording.</p>
                </div>
            `;
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }

    // Copy Verbatim Transcript Button
    if (copyTranscriptBtn) {
        copyTranscriptBtn.addEventListener('click', () => {
            if (!currentData || !currentData.raw_transcript) return;
            navigator.clipboard.writeText(currentData.raw_transcript).then(() => {
                const span = copyTranscriptBtn.querySelector('span');
                const orig = span.textContent;
                span.textContent = 'Copied!';
                setTimeout(() => { span.textContent = orig; }, 2000);
            });
        });
    }

    // New Recording Button
    if (newRecordingBtn) {
        newRecordingBtn.addEventListener('click', () => {
            resetFileInput();
            resultsSection.classList.add('hidden');
            currentData = null;
            document.getElementById('upload-section').scrollIntoView({ behavior: 'smooth' });
        });
    }

    // Copy Full Report
    if (copyReportBtn) {
        copyReportBtn.addEventListener('click', () => {
            if (!currentData) return;
            const textToCopy = formatReportForExport(currentData);
            navigator.clipboard.writeText(textToCopy).then(() => {
                const originalSpan = copyReportBtn.querySelector('span');
                const prev = originalSpan.textContent;
                originalSpan.textContent = 'Copied!';
                setTimeout(() => { originalSpan.textContent = prev; }, 2000);
            });
        });
    }

    // Export TXT
    if (exportTxtBtn) {
        exportTxtBtn.addEventListener('click', () => {
            if (!currentData) return;
            const content = formatReportForExport(currentData);
            downloadFile(content, 'meeting-intelligence-report.txt', 'text/plain');
        });
    }

    // Export Markdown
    if (exportMdBtn) {
        exportMdBtn.addEventListener('click', () => {
            if (!currentData) return;
            const content = formatMarkdownForExport(currentData);
            downloadFile(content, 'meeting-intelligence-report.md', 'text/markdown');
        });
    }

    function formatReportForExport(data) {
        let output = `=======================================================\n`;
        output += `             MEETING INTELLIGENCE REPORT              \n`;
        output += `                 Powered by Vocalis AI                \n`;
        output += `=======================================================\n\n`;

        output += `1. VERBATIM TRANSCRIPTION\n`;
        output += `-------------------------------------------------------\n`;
        output += `${data.raw_transcript || 'N/A'}\n\n\n`;

        output += `2. OVERALL MEETING SUMMARY ${data.is_bilingual ? '(TANGLISH)' : '(ENGLISH)'}\n`;
        output += `-------------------------------------------------------\n`;
        output += `${data.overall_summary || 'N/A'}\n\n\n`;

        output += `3. PERSON-WISE SUMMARY\n`;
        output += `-------------------------------------------------------\n`;
        (data.personwise_summary || []).forEach((item) => {
            output += `[${item.speaker}]:\n${item.summary || item.text}\n\n`;
        });
        output += `\n`;

        output += `4. ACTIONS TO BE DONE (WHO SAID & WHO ASSIGNED TO)\n`;
        output += `-------------------------------------------------------\n`;
        if (data.action_items && data.action_items.length > 0) {
            data.action_items.forEach((act, idx) => {
                const task = act.task || act;
                const raisedBy = act.raised_by || 'Meeting Lead';
                const assignedTo = act.assigned_to || 'Assigned Owner';
                output += `[ ] ${idx + 1}. Task: ${task}\n`;
                output += `       Raised by  : ${raisedBy}\n`;
                output += `       Assigned to: ${assignedTo}\n\n`;
            });
        } else {
            output += `No specific action items were mentioned in this recording.\n\n`;
        }

        return output;
    }

    function formatMarkdownForExport(data) {
        let md = `# Meeting Intelligence Report\n\n`;
        md += `*Generated automatically by **Vocalis AI***\n\n`;
        md += `---\n\n`;

        md += `## 1. 📝 Verbatim Transcription\n\n\`\`\`\n${data.raw_transcript || 'N/A'}\n\`\`\`\n\n`;

        md += `## 2. 📊 Overall Meeting Summary ${data.is_bilingual ? '*(Tanglish)*' : '*(English)*'}\n\n${data.overall_summary || 'N/A'}\n\n`;

        md += `## 3. 👥 Person-wise Summary\n\n`;
        (data.personwise_summary || []).forEach((item) => {
            md += `### ${item.speaker}\n${item.summary || item.text}\n\n`;
        });

        md += `## 4. ✅ Actions To Be Done\n\n`;
        if (data.action_items && data.action_items.length > 0) {
            md += `| # | Task | Raised by (Who said the work) | Assigned to (Who it is assigned to) |\n`;
            md += `|---|---|---|---|\n`;
            data.action_items.forEach((act, idx) => {
                const task = act.task || act;
                const raisedBy = act.raised_by || 'Meeting Lead';
                const assignedTo = act.assigned_to || 'Assigned Owner';
                md += `| ${idx + 1} | ${task} | **${raisedBy}** | **${assignedTo}** |\n`;
            });
        } else {
            md += `*No specific action items were mentioned in this recording.*\n`;
        }
        md += `\n`;

        return md;
    }

    function downloadFile(content, fileName, mimeType) {
        const blob = new Blob([content], { type: `${mimeType};charset=utf-8;` });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", fileName);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
});
