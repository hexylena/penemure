// https://stackoverflow.com/questions/105034/how-do-i-create-a-guid-uuid
function uuid() {
	return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, c => { return (+c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> +c / 4).toString(16) });
}

/* remove need to [...doc.qs].forEach()... */
HTMLCollection.prototype.forEach = Array.prototype.forEach;
NodeList.prototype.forEach = Array.prototype.forEach;
HTMLCollection.prototype.filter = Array.prototype.filter;
NodeList.prototype.filter = Array.prototype.filter;
HTMLCollection.prototype.map = Array.prototype.map;
NodeList.prototype.map = Array.prototype.map;

function autoResize() {
	this.style.height = 'auto';
	this.style.height = this.scrollHeight + 'px';
}
