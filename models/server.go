package models

import (

	"time"
	"strings"
	"path/filepath"
	"text/template"
	"os"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/render"
	"net/http"
)

func (gn *GlobalNotes) Serve() {
	r := chi.NewRouter()

	// A good base middleware stack
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	// Set a timeout value on the request context (ctx), that will signal
	// through ctx.Done() that the request has timed out and further
	// processing should be stopped.
	r.Use(middleware.Timeout(60 * time.Second))

	r.Get("/", gn.serve_index)
	r.Get("/index.html", gn.serve_index)
	r.Get("/search.html", gn.serve_search)
	// r.Route("/notes", func(r chi.Router) {
	// 	// r.With(paginate).Get("/", listArticles)                           // GET /notes
	// 	// r.Get("/", gn.serve_listArticles)                           // GET /notes
	// 	// r.Get("/search", gn.serve_searchArticles)                                  // GET /notes/search
	r.Get("/{articleSlug:[a-f0-9-]+}.html", gn.serve_getArticleBySlug) // GET /notes/<uuid>
	// })

	// Otherwise serve things directly from templates dir.
	workDir, _ := os.Getwd()
	filesDir := http.Dir(filepath.Join(workDir, "templates/"))
	FileServer(r, "/", filesDir)

	http.ListenAndServe(":3333", r)
}

func (gn *GlobalNotes) serve_index(w http.ResponseWriter, r *http.Request) {
	list_tpl_text, err := os.ReadFile("templates/list.html")
	if err != nil {
		logger.Error("Error", "err", err)
	}
	list_tpl, err := template.New("list").Parse(string(list_tpl_text))
	if err != nil {
		logger.Error("Error", "err", err)
	}

	// Render template
	err = list_tpl.Execute(w, gn)
	if err != nil {
		logger.Error("Error", "err", err)
	}
}

func (gn *GlobalNotes) serve_search(w http.ResponseWriter, r *http.Request) {
	list_tpl_text, err := os.ReadFile("templates/search.html")
	if err != nil {
		logger.Error("Error", "err", err)
	}
	list_tpl, err := template.New("list").Parse(string(list_tpl_text))
	if err != nil {
		logger.Error("Error", "err", err)
	}

	// Render template
	err = list_tpl.Execute(w, gn)
	if err != nil {
		logger.Error("Error", "err", err)
	}
}

var ErrNotFound = &ErrResponse{HTTPStatusCode: 404, StatusText: "Resource not found."}

func (gn *GlobalNotes) serve_getArticleBySlug(w http.ResponseWriter, r *http.Request) {
	if pni := chi.URLParam(r, "articleSlug"); pni != "" {
		partial := PartialNoteId(pni)
		note_id, err := gn.GetIdByPartial(partial)
		if err != nil {
			render.Render(w, r, ErrNotFound)
			return
		}
		note := gn.notes[note_id]
		note.Export(gn, w)
	} else {
		render.Render(w, r, ErrNotFound)
		return
	}
}



// FileServer conveniently sets up a http.FileServer handler to serve
// static files from a http.FileSystem.
func FileServer(r chi.Router, path string, root http.FileSystem) {
	if strings.ContainsAny(path, "{}*") {
		panic("FileServer does not permit any URL parameters.")
	}

	if path != "/" && path[len(path)-1] != '/' {
		r.Get(path, http.RedirectHandler(path+"/", 301).ServeHTTP)
		path += "/"
	}
	path += "*"

	r.Get(path, func(w http.ResponseWriter, r *http.Request) {
		rctx := chi.RouteContext(r.Context())
		pathPrefix := strings.TrimSuffix(rctx.RoutePattern(), "/*")
		fs := http.StripPrefix(pathPrefix, http.FileServer(root))
		fs.ServeHTTP(w, r)
	})
}
