1. on client side, date under single project shows "Created Invalid Date", while date in db is correct
2. lets add file upload (fasta files for creating sequences in batch) on client side
3. improve error messages client side: "Invalid input: expected number, received undefined" when you dont choose a project is meh, it should be something like "Project is required"
4. what is more, in such scenario, no error message is visible on client side, in this and other places some toast notifications or any error/success message would be nice. After registering or logging in, there is no notification too.
5. change page title in browser from client to Chromatin Project
6. I cant log out: Uncaught TypeError: logout.mutate is not a function at handleLogout
7. when creating sequence, same sequence data validation as present on backend should be also present on client side (and frontend should show errors related to it, currently its silent 400 without any form error or notificatino popup)