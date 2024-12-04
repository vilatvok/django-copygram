document.addEventListener('DOMContentLoaded', (event) => {
	const csrftoken = Cookies.get("csrftoken")
	const like_button = document.getElementById("likes");
	const like_action = document.getElementById("is_like")
	const likes_count = document.getElementById("total_likes");

	let options = {
		headers: {'X-CSRFToken': csrftoken},
		mode: 'same-origin'
	}
	like_button.addEventListener("click", function(event) {
		event.preventDefault();
		var main_url;
		if (like_action.innerText.trim() === '❤') {
			options.method = 'DELETE'
			main_url = unlike_url
		} else {
			options.method = 'POST'
			main_url = like_url
		}
		fetch(main_url, options)
			.then(response => response.json())
			.then(data => {
				try {
					var total = parseInt(likes_count.innerHTML)
					likes_count.innerHTML = data.status === 'Liked' ? total + 1 : total - 1;
				} catch (error) {
					console.log()
				}
				like_action.innerHTML = data.status === 'Liked' ? `&#10084;` : `&#9825;`
			})
			.catch(error => {
				console.error(error)
			})
		})

	const save_button = document.getElementById("saved");
	save_button.addEventListener("click", function(event){
		event.preventDefault();

		var main_url;
		const btn = save_button.querySelector('.bi.bi-bookmarks')
		if (btn.getAttribute('fill') === 'white') {
			options.method = 'DELETE'
			main_url = unsave_url
		} else {
			options.method = 'POST'
			main_url = save_url
		}
		fetch(main_url, options)
			.then(response => response.json())
			.then(data => {
				console.log(data)
				btn.setAttribute('fill', data.status === 'Saved' ? 'white' : 'black');
			})
			.catch(error => {
				console.error(error)
			})
	})
	const deleteCommentButtons = document.querySelectorAll('.delete-comment');

	function delete_comments(btns) {
		btns.forEach(button => {
			button.addEventListener('click', function(event) {
				event.preventDefault()
				const comment = button.getAttribute('id')
				const split = comment.split('-')
				const comment_id = split[1]
				const comment_url = `https://copygram.com/posts/${post_id}/delete-comment/${comment_id}/`
				// Make a request to delete the comment
				options.method = 'DELETE'
				fetch(comment_url, options)
					.then(response => response.json())
					.then(data => {
						if (data["status"] == "Deleted") {
							const commentElement = document.querySelector(`.comment-frame-${comment_id}`)
							commentElement.remove()
						}
					})
					.catch(error => {
						console.error("Fetch error", error);
					});
			});
		})
	}
	delete_comments(deleteCommentButtons);

	const playVideo = document.querySelectorAll('.playVideo')
	playVideo.forEach(btn => {
		btn.addEventListener('click', function(event) {
			if (btn.paused){
				btn.play();
			} else {
				btn.pause();
			}
		})
	})
})