const form = document.querySelector('.contact form');

if (form) {
  form.addEventListener('submit', (e) => {
    const first = (form.querySelector('input[name="first_name"]') || { value: '' }).value.trim();
    const last = (form.querySelector('input[name="last_name"]') || { value: '' }).value.trim();
    const email = (form.querySelector('input[name="email"]') || { value: '' }).value.trim();
    const message = (form.querySelector('textarea[name="message"]') || { value: '' }).value.trim();

    if ((!first && !last) || !email || !message) {
      e.preventDefault();
      alert('Please fill out all required fields');
    }
    // If valid, allow normal submission to server
  });
}