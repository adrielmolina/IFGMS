/**
 * Global Input Restrictions Script
 * Works for Members, Claims, and other modules.
 * 
 * Add new field IDs to the appropriate arrays below.
 */
document.addEventListener("DOMContentLoaded", () => {

  // ===== COMMON ALLOWED KEYS =====
  const allowedKeys = [
    "Backspace", "Tab", "Escape", "Delete",
    "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown",
    "Home", "End"
  ];

  // ===== 1️⃣ NAME FIELDS (letters, space, apostrophe, hyphen only) =====
  const namePattern = /^[a-zA-Z' -]$/;
  const nameFields = [
    // Members module
    "fname", "mname", "lname",
    // Claims module
    "claimant_fname", "claimant_mname", "claimant_lname",
    "received_by"
  ];

  nameFields.forEach(id => {
    const input = document.getElementById(id);
    if (!input) return;

    // Prevent disallowed keys
    input.addEventListener("keydown", event => {
      if (allowedKeys.includes(event.key)) return;
      if (!namePattern.test(event.key)) event.preventDefault();
    });

    // Prevent invalid paste
    input.addEventListener("paste", event => {
      const pasted = (event.clipboardData || window.clipboardData).getData("text");
      if ([...pasted].some(char => !namePattern.test(char))) event.preventDefault();
    });
  });

  // ===== 2️⃣ CONTACT NUMBER FIELDS (digits only) =====
  const digitFields = [
    "contact", // Members
    "entry_or_no",
    "claimant_contact_no" // Claims
  ];

  digitFields.forEach(id => {
    const input = document.getElementById(id);
    if (!input) return;

    input.addEventListener("keydown", event => {
      if (allowedKeys.includes(event.key)) return;
      if (!/^\d$/.test(event.key)) event.preventDefault();
    });

    input.addEventListener("paste", event => {
      const pasted = (event.clipboardData || window.clipboardData).getData("text");
      if (!/^\d+$/.test(pasted)) event.preventDefault();
    });
  });

  // ===== 3️⃣ MAAB NUMBER FIELDS (digits only, with auto-prefix) =====
  
  // Only apply restrictions to TEXT inputs, not SELECT dropdowns
  //const maabNoField = document.getElementById('maab_no');
  
  if (maabNoField && maabNoField.tagName === 'INPUT') {
    // Store the current prefix for this field
    let currentPrefix = '';

    // Function to update prefix based on category
    function updateMaabPrefix() {
      const categorySelect = document.getElementById('maab_cat');
      if (categorySelect) {
        const category = categorySelect.value;
        const prefixMap = {
          'Classic': 'PC',
          'Bronze': 'PB', 
          'Silver': 'PS',
          'Gold': 'PG',
          'Platinum': 'PP',
          'Safe Card': 'PEP',
          'Senior': 'S',
          'Senior+': 'SP'
        };
        currentPrefix = prefixMap[category] || '';
        
        // Update placeholder to show the format
        maabNoField.placeholder = `Enter 7 digits (${currentPrefix} + numbers)`;
      }
    }

    // Initialize prefix and set up category change listener
    if (document.getElementById('maab_cat')) {
      updateMaabPrefix();
      document.getElementById('maab_cat').addEventListener('change', updateMaabPrefix);
    }

    maabNoField.addEventListener("keydown", event => {
      if (allowedKeys.includes(event.key)) return;
      if (!/^\d$/.test(event.key)) event.preventDefault();
    });

    maabNoField.addEventListener("input", function() {
      // Remove any non-digit characters
      this.value = this.value.replace(/\D/g, '');
      
      // Limit to 7 digits
      if (this.value.length > 7) {
        this.value = this.value.slice(0, 7);
      }
    });

    maabNoField.addEventListener("paste", event => {
      const pasted = (event.clipboardData || window.clipboardData).getData("text");
      const digitsOnly = pasted.replace(/\D/g, '').slice(0, 7);
      event.preventDefault();
      maabNoField.value = digitsOnly;
    });

    // Add focus/blur handlers to show full MAAB number with prefix
    maabNoField.addEventListener("focus", function() {
      // Remove prefix when focused for editing
      if (currentPrefix && this.value.startsWith(currentPrefix)) {
        this.value = this.value.replace(currentPrefix, '');
      }
    });

    maabNoField.addEventListener("blur", function() {
      // Add prefix back when blurred (if we have numbers)
      if (currentPrefix && this.value && /^\d+$/.test(this.value)) {
        this.value = currentPrefix + this.value.padStart(7, '0');
      }
    });
    
    console.log('✅ MAAB No restrictions applied to text input');
  } else if (maabNoField && maabNoField.tagName === 'SELECT') {
    console.log('✅ MAAB No is a dropdown - no restrictions needed');
    // No restrictions needed for dropdown
  } else {
    console.log('❌ MAAB No field not found or not applicable');
  }
  
  // ===== 4️⃣ AMOUNT FIELDS (digits + decimal point) =====
  const amountFields = [
    "chinabank_amount",
    "bpi_amount"
  ];

  amountFields.forEach(id => {
    const input = document.getElementById(id);
    if (!input) return;

    input.addEventListener("keydown", event => {
      if (allowedKeys.includes(event.key)) return;
      if (!/^[0-9.]$/.test(event.key)) event.preventDefault();
    });

    input.addEventListener("paste", event => {
      const pasted = (event.clipboardData || window.clipboardData).getData("text");
      if (!/^[0-9.]+$/.test(pasted)) event.preventDefault();
    });
  });

  // ===== 5️⃣ CHECK NUMBER FIELDS (letters, digits, hyphen) =====
  const checkNoFields = [
    "chinabank_check_no",
    "bpi_check_no"
  ];

  checkNoFields.forEach(id => {
    const input = document.getElementById(id);
    if (!input) return;

    input.addEventListener("keydown", event => {
      if (allowedKeys.includes(event.key)) return;
      if (!/^[a-zA-Z0-9-]$/.test(event.key)) event.preventDefault();
    });

    input.addEventListener("paste", event => {
      const pasted = (event.clipboardData || window.clipboardData).getData("text");
      if (!/^[a-zA-Z0-9-]+$/.test(pasted)) event.preventDefault();
    });
  });

  // ===== 7️⃣ DATE FIELDS ENFORCEMENT =====
  // Ensure OR date field uses datepicker
  const dateFields = ["entry_or_date", "bdate", "declare_date", "dec_date", "eff_date"];

  dateFields.forEach(id => {
    const input = document.getElementById(id);
    if (!input) return;

    // Change type to date if it's not already
    if (input.type !== 'date' && id === 'entry_or_date') {
      input.type = 'date';
    }

    // Prevent manual text input for date fields
    input.addEventListener("keydown", event => {
      if (allowedKeys.includes(event.key)) return;
      event.preventDefault();
    });
  });
});