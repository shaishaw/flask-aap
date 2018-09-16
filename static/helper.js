// Helper function to delete user
function userdel(obj)
{
    if(!confirm("Are you sure to remove this user from the system?")){
        return false;
    }
    var url = obj.getAttribute('href');
    var form = document.createElement('form');
    form.setAttribute('method', 'post');
    form.setAttribute('action', url);

    document.body.appendChild(form);
    form.submit();

    return false;
}
