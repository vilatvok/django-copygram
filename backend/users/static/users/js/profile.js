document.addEventListener('DOMContentLoaded', (event) => {
	const csrftoken = Cookies.get("csrftoken")
	const followBtn = document.getElementById("follow")
	const followersElement = document.getElementById("followers")
	followBtn.addEventListener('click', function(event) {
		event.preventDefault();
		let main_url;
		let options = {
			headers: {'X-CSRFToken': csrftoken},
			mode: 'same-origin'
		}
		if (followBtn.innerHTML.trim() === 'Unfollow') {
			options.method = 'DELETE'
			main_url = unfollow_endpoint
		} else {
			options.method = 'POST'
			main_url = follow_endpoint
		}
		var total = parseInt(followersElement.innerHTML)
		fetch(main_url, options)
			.then(response => response.json())
			.then(data => {
				switch (data.status) {
					case 'Followed':
						followBtn.innerHTML = 'Unfollow'
						followersElement.innerHTML = total + 1 +  ''
						break;
					case 'Request was sent':
						followBtn.innerHTML = 'Cancel'
						break;
					case 'Unfollowed':
						followBtn.innerHTML = 'Follow'
						followersElement.innerHTML = total - 1 + ' '
					case 'Canceled':
						followBtn.innerHTML = 'Follow'
						break;
				}
			})
			.catch(error => {
				console.error(error);
			})
	})
})