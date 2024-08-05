package models

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"text/template"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	// "github.com/go-chi/render"
	"net/http"

	pmc "github.com/hexylena/pm/config"
)

var config pmc.HxpmConfig

func (gn *GlobalNotes) Serve(_config pmc.HxpmConfig) {
	r := chi.NewRouter()
	r.Mount(config.ExportPrefix, gn.MainRoutes(_config))
	r.Get("/", func(w http.ResponseWriter, r *http.Request) {
		http.Redirect(w, r, config.ExportPrefix, http.StatusFound)
	})
	r.NotFound(gn.serve_404)
	http.ListenAndServe(":3333", r)
}

func (gn *GlobalNotes) MainRoutes(_config pmc.HxpmConfig) chi.Router {
	r := chi.NewRouter()
	config = _config

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

	fmt.Println("Starting server on port 3333")

	logger.Info("Starting server", "port", 3333)
	r.NotFound(gn.serve_404)

	// Otherwise serve things directly from templates dir.
	workDir, _ := os.Getwd()
	filesDir := http.Dir(filepath.Join(workDir, "templates/assets/"))
	FileServer(r, "/assets", filesDir)
	return r
}

func get_template(templateName string) *template.Template {
	tmpl, err := template.New("").ParseFiles(fmt.Sprintf("templates/%s.html", templateName), "templates/base.html")
	if err != nil {
		logger.Error("Error", "err", err)
	}
	return tmpl
}

type templateContext struct {
	Gn     *GlobalNotes
	Config pmc.HxpmConfig
}

func (gn *GlobalNotes) serve_404(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(404)
	tmpl := get_template("404")
	err := tmpl.ExecuteTemplate(w, "base", templateContext{gn, config})
	if err != nil {
		logger.Error("Error", "err", err)
	}
}

func (gn *GlobalNotes) serve_index(w http.ResponseWriter, r *http.Request) {
	tmpl := get_template("list")
	err := tmpl.ExecuteTemplate(w, "base", templateContext{Gn: gn, Config: config})
	if err != nil {
		logger.Error("Error", "err", err)
	}
}

func (gn *GlobalNotes) serve_search(w http.ResponseWriter, r *http.Request) {
	tmpl := get_template("search")
	err := tmpl.ExecuteTemplate(w, "base", templateContext{Gn: gn, Config: config})
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
			gn.serve_404(w, r)
			return
		}
		note := gn.notes[note_id]
		note.Export(gn, w, config)
	} else {
		gn.serve_404(w, r)
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
		r.Get(path, http.RedirectHandler(path+"/", http.StatusFound).ServeHTTP)
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
