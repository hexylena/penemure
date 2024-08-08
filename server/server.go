// Package server provides functionality for the server.
package server

import (
	"encoding/json"
	"fmt"
	"strings"
	"text/template"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	// "github.com/go-chi/render"
	"net/http"

	"embed"

	pma "github.com/hexylena/pm/adapter"
	pmc "github.com/hexylena/pm/config"
	pml "github.com/hexylena/pm/log"
	pmm "github.com/hexylena/pm/models"
)

var gn *pmm.GlobalNotes
var ga *pma.TaskAdapter
var config *pmc.HxpmConfig
var logger = pml.L("server")
var templateFS *embed.FS

func Serve(_gn *pmm.GlobalNotes, _ga *pma.TaskAdapter, _config *pmc.HxpmConfig, _templates *embed.FS) {
	config = _config
	ga = _ga
	gn = _gn
	templateFS = _templates

	r := chi.NewRouter()
	r.Mount(config.ExportPrefix, MainRoutes())

	if config.ExportPrefix != "/" {
		r.Get("/", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, config.ExportPrefix, http.StatusFound)
		})
	}
	r.NotFound(serve_404)
	logger.Info("Starting server", "addr", config.ServerBindAddr)
	err := http.ListenAndServe(config.ServerBindAddr, r)
	if err != nil {
		logger.Error("Error", "err", err)
	}
}

func MainRoutes() chi.Router {
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
	context := map[string]string{}

	r.Get("/", func(w http.ResponseWriter, r *http.Request) {
		server_fn("list", w, r, context)
	})
	r.Get("/manifest.json", serve_manifest_json)
	r.Get("/index.html", func(w http.ResponseWriter, r *http.Request) {
		server_fn("list", w, r, context)
	})
	r.Get("/search.html", func(w http.ResponseWriter, r *http.Request) {
		server_fn("search", w, r, context)
	})
	r.Get("/time", func(w http.ResponseWriter, r *http.Request) {
		server_fn("time", w, r, context)
	})
	r.Post("/time", func(w http.ResponseWriter, r *http.Request) {
		// handle form
		err := r.ParseForm()
		if err != nil {
			logger.Error("Unparseable data", "err", err)
			context["error"] = fmt.Sprintf("Unparseable data, %s", err)
		} else {
			formData := r.Form
			processTimeSubmission(formData)
		}

		// process form data
		server_fn("time", w, r, context)
	})

	r.Get("/new", func(w http.ResponseWriter, r *http.Request) {
		server_fn("new", w, r, context)
	})
	r.Post("/new", func(w http.ResponseWriter, r *http.Request) {
		err := r.ParseForm()
		if err != nil {
			logger.Error("Unparseable data", "err", err)
			context["error"] = fmt.Sprintf("Unparseable data, %s", err)
		} else {
			formData := r.Form
			note := processNoteSubmission(formData)
			context["success"] = fmt.Sprintf(`Saved new note as <a href="%s.html">%s</a>`, note.NoteId, note.Title)
		}

		// process form data
		server_fn("new", w, r, context)
	})
	// r.Route("/notes", func(r chi.Router) {
	// 	// r.With(paginate).Get("/", listArticles)                           // GET /notes
	// 	// r.Get("/", gn.serve_listArticles)                           // GET /notes
	// 	// r.Get("/search", gn.serve_searchArticles)                                  // GET /notes/search
	r.Get("/{articleSlug:[a-f0-9-]+}.html", serve_getArticleBySlug) // GET /notes/<uuid>
	// })

	r.NotFound(serve_404)

	// Otherwise serve things directly from templates dir.
	// workDir, _ := os.Getwd()
	// filesDir := http.Dir(filepath.Join(workDir, "templates/assets/"))
	// fmt.Println(filesDir)
	httpfs := http.FS(templateFS)
	FileServer(r, "/assets", config.ExportPrefix, httpfs)
	return r
}

func get_template(templateName string) *template.Template {
	tmpl, err := template.New("").ParseFS(templateFS, fmt.Sprintf("templates/%s.html", templateName), "templates/base.html")
	if err != nil {
		logger.Error("Error", "err", err)
	}
	return tmpl
}

type templateContext struct {
	Gn      *pmm.GlobalNotes
	Config  *pmc.HxpmConfig
	Context map[string]string
}

func serve_404(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusNotFound)
	server_fn("404", w, r, map[string]string{})
}

func server_fn(fn string, w http.ResponseWriter, r *http.Request, context map[string]string) {
	tmpl := get_template(fn)
	err := tmpl.ExecuteTemplate(w, "base", templateContext{gn, config, context})
	if err != nil {
		logger.Error("Error", "err", err)
	}
}

func serve_manifest_json(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(config.Manifest())
}

var ErrNotFound = &ErrResponse{HTTPStatusCode: 404, StatusText: "Resource not found."}

func serve_getArticleBySlug(w http.ResponseWriter, r *http.Request) {
	if pni := chi.URLParam(r, "articleSlug"); pni != "" {
		partial := pmm.PartialNoteId(pni)
		note_id, err := gn.GetIdByPartial(partial)
		if err != nil {
			serve_404(w, r)
			return
		}
		note := gn.GetNoteByID(note_id)
		note.Export(gn, w, config)
	} else {
		serve_404(w, r)
		return
	}
}

// FileServer conveniently sets up a http.FileServer handler to serve
// static files from a http.FileSystem.
func FileServer(r chi.Router, path string, prefix string, root http.FileSystem) {
	if strings.ContainsAny(path, "{}*") {
		panic("FileServer does not permit any URL parameters.")
	}

	if path != "/" && path[len(path)-1] != '/' {
		r.Get(path, http.RedirectHandler(path+"/", http.StatusFound).ServeHTTP)
		path += "/"
	}
	path += "*"

	r.Get(path, func(w http.ResponseWriter, r *http.Request) {
		// rctx := chi.RouteContext(r.Context())
		// pathPrefix := strings.TrimSuffix(rctx.RoutePattern(), "/*")
		// fmt.Println(pathPrefix)
		fs := http.StripPrefix(prefix, http.FileServer(root))

		// we don't strip /assets because that's actually our folder name and
		// where we want to serve it.
		// fs := http.FileServer(root)

		w.Header().Set("Cache-Control", "public, max-age=86400") // Set cache control header to allow caching for 24 hours
		fs.ServeHTTP(w, r)
	})
}
