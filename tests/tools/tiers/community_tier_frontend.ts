interface UserData {
    id: number;
    role: 'admin' | 'user';
}

function sendData(data: UserData) {
    fetch('/api/process', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}
