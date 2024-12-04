document.addEventListener('DOMContentLoaded', (event) => {
	const csrftoken = Cookies.get("csrftoken")
	const users = document.querySelectorAll(".me-1")
	users.forEach(button => {
		button.addEventListener('click', function(event) {
			event.preventDefault();
			const user_ = button.getAttribute('id')
			const split = user_.split('-')
			const user_slug = split[1]
			const followersElement = document.querySelector(`[id="followers-${user_slug}"]`);
			
			let main_url;
			let options = {
				headers: {'X-CSRFToken': csrftoken},
				mode: 'same-origin'
			}
			
			if (button.innerHTML.trim() === 'Unfollow') {
				options.method = 'DELETE'
				main_url = unfollow_endpoint.replace('0', user_slug)
			} else {
				options.method = 'POST'
				main_url = follow_endpoint.replace('0', user_slug)
			}
			
			var total = parseInt(followersElement.innerHTML)
			fetch(main_url, options)
				.then(response => response.json())
				.then(data => {
					switch (data.status) {
						case 'Followed':
							button.innerHTML = 'Unfollow'
							followersElement.innerHTML = total + 1 +  ''
							break;
						case 'Request was sent':
							button.innerHTML = 'Cancel'
							break;
						case 'Unfollowed':
							button.innerHTML = 'Follow'
							followersElement.innerHTML = total - 1 + ' '
						case 'Canceled':
							button.innerHTML = 'Follow'
							break;
					}
				})
				.catch(error => {
					console.error(error);
				})
		})
	})
})