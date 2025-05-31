function renderEntriesTable(data) {
    console.log("Entries data:", data);
    const container = document.getElementById('entries_table');
    document.getElementById('entries_table').innerHTML = '';

                new Handsontable(container, {
                    data,
                    colHeaders: [
                        'Entry ID', 'MAAB Category', 'MAAB No', 'First Name', 'Middle Name', 'Last Name', 'Suffix',
                        'Birthdate', 'Age', 'Sex', 'Contact #', 'Email', 'Address', 'Blood Type', 'ID Received',
                        'Declared', 'Declaration Date', 'Paid', 'OR #', 'OR Date', 'Remarks', 'Tags'
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
                    { data: 'tags' }
                    ],
                    rowHeaders: true,
                    stretchH: 'all',
                    autoWrapRow: false,
                    autoWrapCol: false,
                    licenseKey: 'non-commercial-and-evaluation'
                });

}

// Make the function available globally
window.renderEntriesTable = renderEntriesTable;