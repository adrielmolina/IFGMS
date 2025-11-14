function renderEntriesTable(data) {
    console.log("Entries data:", data);
    const container = document.getElementById('entries_table');
    document.getElementById('entries_table').innerHTML = '';

    // Fixed height that works well in overlay
    const fixedHeight = 400; // Optimal for overlay viewing

    new Handsontable(container, {
        data,
        colHeaders: [
            'Entry ID', 'MAAB Category', 'MAAB No', 'First Name', 'Middle Name', 'Last Name', 'Suffix',
            'Birthdate', 'Age', 'Sex', 'Contact #', 'Email', 'Address', 'Blood Type', 'ID Received',
            'Declared', 'Declaration Date', 'Paid', 'OR #', 'OR Date', 'Remarks', 'Tags', 'Dispatch Ready', 'Dispatch ID'
        ],
        columns: [
            { data: 'entry_id', readOnly: true },
            { data: 'maab_category' },
            { data: 'maab_no' },
            { data: 'first_name' },
            { data: 'middle_name' },
            { data: 'last_name' },
            { data: 'suffix' },
            { 
                data: 'birth_date',
                type: 'date',
                dateFormat: 'MM-DD-YYYY',
                correctFormat: true,
                allowInvalid: false
            },
            { data: 'age', readOnly: true },
            { data: 'sex' },
            { data: 'contact_no' },
            { data: 'email' },
            { data: 'address' },
            { data: 'blood_type' },
            { data: 'id_received', type: 'checkbox' },         
            { data: 'declared', type: 'checkbox' },
            { 
                data: 'declaration_date',
                type: 'date',
                dateFormat: 'MM-DD-YYYY',
                correctFormat: true,
                allowInvalid: false
            },
            { data: 'paid', type: 'checkbox' },
            { data: 'OR_num' },
            { 
                data: 'OR_date',
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
        autoWrapRow: false,
        autoWrapCol: false,
        readOnly: true,
        search: true,
        filters: true,
        dropdownMenu: true,
        licenseKey: 'non-commercial-and-evaluation',
        width: '100%',
        height: fixedHeight,
        // Better scrolling performance
        viewportRowRenderingOffset: 10,
        viewportColumnRenderingOffset: 10,
    });

    // Set up horizontal scroll for entries table
    setTimeout(() => {
        ensureEntriesTableScroll();
    }, 100);
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

window.renderEntriesTable = renderEntriesTable;