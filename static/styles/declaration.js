document.addEventListener("DOMContentLoaded", () => {
  const rowChecks = document.querySelectorAll(".row-check");
  const selectAllCheckbox = document.getElementById("selectAll");
  const transmitBtn = document.querySelector(".btn.transmit");
  const historyBtn = document.querySelector(".btn.history");
  const selectAllBtn = document.querySelector(".btn.select-all");
  const summaryText = document.getElementById("summaryText");
  const tableRows = document.querySelectorAll("#dataTable tbody tr");

  function updateSelection() {
    const checkedCount = document.querySelectorAll(".row-check:checked").length;
    const totalCount = tableRows.length;

    // Enable/disable transmit + history
    transmitBtn.disabled = checkedCount === 0;
    historyBtn.disabled = checkedCount === 0;

    // Update button labels
    transmitBtn.textContent = `Transmit (${checkedCount})`;
    historyBtn.textContent = `History (${checkedCount})`;

    // Update summary text
    summaryText.textContent = `Showing ${totalCount} of ${totalCount} declarations • ${checkedCount} selected`;

    // Sync header checkbox
    selectAllCheckbox.checked = checkedCount === totalCount;
  }
 

  // Row checkbox change
  rowChecks.forEach(cb => {
    cb.addEventListener("change", updateSelection);
  });

  // Header checkbox (select all in table)
  selectAllCheckbox.addEventListener("change", () => {
    rowChecks.forEach(cb => cb.checked = selectAllCheckbox.checked);
    updateSelection();
  });

  // "Select All" action button
  selectAllBtn.addEventListener("click", () => {
    const isSelecting = selectAllBtn.textContent === "Select All";
    rowChecks.forEach(cb => cb.checked = isSelecting);
    selectAllCheckbox.checked = isSelecting;
    selectAllBtn.textContent = isSelecting ? "Deselect All" : "Select All";
    updateSelection();
  });


  updateSelection();
});
