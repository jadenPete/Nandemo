import React from "react"
import * as ReactDOM from "react-dom"

function App(props: {emptyChats: string}) {
	const [chats, setChats] = React.useState(props.emptyChats);

	React.useEffect(() => {
		fetch("/").then(response => response.text()).then(text => {
			setChats(text)
		})
	}, []);

	return <>
		<h1>Hello, world!</h1>
		<h2>Current state:</h2>

		<p>{chats}</p>

		<button onClick={() => setChats(props.emptyChats)}>Clear</button>
	</>
}

ReactDOM.render(<App emptyChats="We have none yet"></App>, document.querySelector(".root"))
