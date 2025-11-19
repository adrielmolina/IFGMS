let debounceTimer;

function renderEntriesTable(data) {
    console.log("🎯 RENDERING ENTRIES TABLE with data:", data);
    const container = document.getElementById('entries_table');
    
    // Clear previous table
    container.innerHTML = '';
    
    const fixedHeight = 400;
    
    // ✅ CRITICAL: Store the instance globally
    window.entriesHotInstance = new Handsontable(container, {
        data: data,
        colHeaders: [
            'Entry ID', 'MAAB Category', 'MAAB No', 'First Name', 'Middle Name', 'Last Name', 'Suffix',
            'Birthdate', 'Age', 'Sex', 'Contact #', 'Email', 'Address', 'Blood Type', 'ID Received',
            'Declared', 'Declaration Date', 'Paid', 'OR #', 'OR Date', 'Remarks', 'Tags', 'Dispatch Ready', 'Dispatch ID'
        ],
        columns: [
            { data: 'entry_id', readOnly: true },
            { 
                data: 'maab_category',
                type: 'dropdown',
                source: ['Classic', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Safe Card', 'Senior', 'Senior+'],
                strict: true,
                allowInvalid: false
            },
            { data: 'maab_no' },
            { data: 'first_name' },
            { data: 'middle_name' },
            { data: 'last_name' },
            { 
                data: 'suffix',
                type: 'dropdown',
                source: ['NA', 'Jr', 'Sr', 'II', 'III', 'IV', 'V', 'VI', 'VII'],
                strict: true,
                allowInvalid: false
            },
            { 
                data: 'birth_date',
                type: 'date',
                dateFormat: 'YYYY-MM-DD',
                correctFormat: true,
                allowInvalid: false
            },
            { data: 'age', readOnly: true }, // Age is read-only
            { 
                data: 'sex',
                type: 'dropdown',
                source: ['', 'male', 'female', 'Prefer not to say'],
                strict: true,
                allowInvalid: false
            },
            { data: 'contact_no' },
            { data: 'email' },
            { data: 'address' },
            { 
                data: 'blood_type',
                type: 'dropdown',
                source: ['', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
                strict: true,
                allowInvalid: false
            },
            { data: 'id_received', type: 'checkbox', className: 'htCenter' },         
            { data: 'declared', type: 'checkbox', className: 'htCenter' },
            { 
                data: 'declaration_date',
                type: 'date',
                dateFormat: 'YYYY-MM-DD',
                correctFormat: true,
                allowInvalid: false
            },
            { data: 'paid', type: 'checkbox', className: 'htCenter' },
            { data: 'OR_num' },
            { 
                data: 'OR_date',
                type: 'date',
                dateFormat: 'YYYY-MM-DD',
                correctFormat: true,
                allowInvalid: false
            },
            { data: 'remarks' },
            { data: 'tags' },
            { data: 'dispatch_ready', type: 'checkbox', className: 'htCenter' },
            { data: 'dispatch_id' }
        ],
        rowHeaders: true,
        stretchH: 'all',
        autoWrapRow: false,
        autoWrapCol: false,
        readOnly: false,
        search: true,
        filters: true,
        dropdownMenu: true,
        licenseKey: 'non-commercial-and-evaluation',
        width: '100%',
        height: fixedHeight,
        viewportRowRenderingOffset: 10,
        viewportColumnRenderingOffset: 10,

        // ✅ ADD AGE CALCULATION WHEN BIRTHDATE CHANGES
        afterChange: function(changes, source) {
            if (source === 'loadData') return;
            
            clearTimeout(debounceTimer);
            
            debounceTimer = setTimeout(() => {
                if (changes) {
                    changes.forEach(([row, prop, oldValue, newValue]) => {
                        console.log(`Changed: row ${row}, prop ${prop}, from "${oldValue}" to "${newValue}"`);
                        
                        // If birthdate column changed, calculate age
                        if (prop === 'birth_date' && newValue) {
                            calculateAgeForTableRow(row, newValue);
                        }
                        
                        const rowData = this.getSourceDataAtRow(row);
                        updateEntryInBackend(rowData);
                    });
                }
            }, 1000);
        },

        // ✅ ADD CLICK HANDLER DIRECTLY IN THE TABLE
        afterOnCellMouseDown: function(event, coords, TD) {
            console.log('🖱️ Handsontable cell clicked at row:', coords.row, 'col:', coords.col);
            
            if (coords.row >= 0) {
                const rowData = this.getSourceDataAtRow(coords.row);
                console.log('📊 Row data retrieved:', rowData);
                
                if (rowData && rowData.entry_id) {
                    console.log('✅ SUCCESS: Found entry with ID:', rowData.entry_id);
                    
                    // Call the global populate function
                    if (window.populateEntryForm) {
                        window.populateEntryForm(rowData);
                    } else {
                        console.error('❌ populateEntryForm function not found globally');
                    }
                } else {
                    console.warn('⚠️ No entry_id found in row data');
                }
            }
        },

        // Custom dropdown styling
        cells: function(row, col, prop) {
            const cellProperties = {};
            
            // Add custom class for dropdown cells
            if (['maab_category', 'suffix', 'sex', 'blood_type'].includes(prop)) {
                cellProperties.className = 'dropdown-cell';
            }
            
            // Center align checkboxes
            if (['id_received', 'declared', 'paid', 'dispatch_ready'].includes(prop)) {
                cellProperties.className = 'checkbox-cell htCenter';
            }
            
            return cellProperties;
        }
    });

    console.log('✅ Entries table instance created and stored globally:', window.entriesHotInstance);

    // Calculate ages for existing rows with birthdates when table loads
    setTimeout(() => {
        const entriesTable = window.entriesHotInstance;
        if (entriesTable && entriesTable.getData) {
            const data = entriesTable.getData();
            data.forEach((row, index) => {
                if (row.birth_date) {
                    calculateAgeForTableRow(index, row.birth_date);
                }
            });
        }
        
        ensureEntriesTableScroll();
    }, 500);
}

// ✅ ADD THIS FUNCTION TO CALCULATE AGE FOR TABLE ROWS
function calculateAgeForTableRow(rowIndex, birthdate) {
    const entriesTable = window.entriesHotInstance;
    if (!entriesTable) {
        console.error('Entries table instance not found');
        return;
    }
    
    console.log(`🔄 Calculating age for row ${rowIndex} with birthdate: ${birthdate}`);
    
    try {
        const birthDate = new Date(birthdate);
        const today = new Date();
        
        // Validate date is not in future
        if (birthDate > today) {
            console.warn('Birthdate cannot be in the future');
            return;
        }
        
        let age = today.getFullYear() - birthDate.getFullYear();
        const monthDiff = today.getMonth() - birthDate.getMonth();
        
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
            age--;
        }
        
        // Update the age column in the table
        entriesTable.setDataAtRowProp(rowIndex, 'age', age);
        console.log(`✅ Age calculated: ${age} for row ${rowIndex}`);
        
    } catch (error) {
        console.error('Error calculating age:', error);
    }
}

function ensureEntriesTableScroll() {
    const entriesTableContainer = document.querySelector('#overlay .table-container');
    const entriesTable = document.getElementById('entries_table');
    
    if (entriesTableContainer && entriesTable) {
        const requiredWidth = 24 * 171;
        entriesTable.style.minWidth = requiredWidth + 'px';
        entriesTableContainer.style.overflowX = 'auto';
        entriesTableContainer.style.overflowY = 'hidden';
    }
}

async function updateEntryInBackend(entryData) {
    try {
        const response = await fetch('/api/save_entry_update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(entryData)
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const result = await response.json();
        console.log('Update successful:', result);
        
        // Update dispatch ready status after saving
        setTimeout(() => {
            if (window.updateDispatchReadyFromEntries) {
                window.updateDispatchReadyFromEntries();
            }
        }, 500);
    } catch (error) {
        console.error('Error updating entry:', error);
    }
}

window.renderEntriesTable = renderEntriesTable;