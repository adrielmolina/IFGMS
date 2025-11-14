
let debounceTimer; // Timer identifier for debouncing

function renderEntriesTable(data) {
    console.log("Entries data:", data);
    const container = document.getElementById('entries_table');
    document.getElementById('entries_table').innerHTML = '';
                
    
                new Handsontable(container, {
                    data,
                    colHeaders: [
                        'Entry ID', 'MAAB Category', 'MAAB No', 'First Name', 'Middle Name', 'Last Name', 'Suffix',
                        'Birthdate', 'Age', 'Sex', 'Contact #', 'Email', 'Address', 'Blood Type', 'ID Received',
                        'Declared', 'Declaration Date', 'Paid', 'OR #', 'OR Date', 'Remarks', 'Tags', 'Dispatch Ready', 'Dispatch ID'
                    ],
                    /* fill with actual data */
                    columns: [
                        { data: 'entry_id', readOnly: true },
                        { data: 'maab_category' },
                        { data: 'maab_no' },
                        { data: 'first_name' },
                        { data: 'middle_name' },
                        { data: 'last_name' },
                        { data: 'suffix' },
                        {   data: 'birth_date',
                            type: 'date',
                            dateFormat: 'MM-DD-YYYY',
                            correctFormat: true,
                            allowInvalid: false },
                        { data: 'age', readOnly: true },
                        { data: 'sex' },
                        { data: 'contact_no' },
                        { data: 'email' },
                        { data : 'address' },
                        { data: 'blood_type' },
                        { data: 'id_received', type: 'checkbox' },         
                        { data: 'declared', type: 'checkbox' },
                        {   data: 'declaration_date',
                            type: 'date',
                            dateFormat: 'MM-DD-YYYY',
                            correctFormat: true,
                            allowInvalid: false },
                        { data: 'paid', type: 'checkbox' },
                        { data: 'OR_num' },
                        {   data: 'OR_date',
                            type: 'date',
                            dateFormat: 'MM-DD-YYYY',
                            correctFormat: true,
                            allowInvalid: false
                        },
                        { data: 'remarks' },
                        { data: 'tags' },
                        { data: 'dispatch_ready', type: 'checkbox' },
                        { data: 'dispatch_id' }
                    ],
                    rowHeaders: true,
                    stretchH: 'all',
                    autoWrapRow: false,
                    autoWrapCol: false,
                    licenseKey: 'non-commercial-and-evaluation',

                    // ADD THE EVENT LISTENER HERE
                    afterChange: function(changes, source) {
                        // Prevent firing during initial load
                        if (source === 'loadData') return;
                        
                        // Clear the previous timer
                        clearTimeout(debounceTimer);
                        
                        // Set a new timer
                        debounceTimer = setTimeout(() => {
                            if (changes) {
                                changes.forEach(([row, prop, oldValue, newValue]) => {
                                    console.log(`Changed: row ${row}, prop ${prop}, from "${oldValue}" to "${newValue}"`);
                                    
                                    // Get the entire row data
                                    const rowData = this.getSourceDataAtRow(row);
                                    
                                    // Call your fetch function
                                    updateEntryInBackend(rowData);
                                });
                            }
                        }, 1000); // Wait 1 second after last change
                    }
                });

}

// Your fetch function
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
    } catch (error) {
        console.error('Error updating entry:', error);
        // You might want to show an error message to the user here
    }
}

// Make the function available globally
window.renderEntriesTable = renderEntriesTable;