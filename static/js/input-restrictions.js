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

  // ===== 6️⃣ FUTURE EXTENSIONS =====
  // Add your next module’s field IDs here
  // Example:
  // const emailFields = ["member_email", "claimant_email"];
  // const addressFields = ["member_address", "claim_address"];
});
