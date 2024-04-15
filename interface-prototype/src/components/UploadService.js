class UploadFilesService {

  async upload(fileName, fileData, target, onUploadProgress) {

    const baseURL = import.meta.env.DEV ? import.meta.env.VITE_DEV_MIDDLEWARE_BASE + '/api': "/api";
    // const formData = new FormData();
    // console.log("...Uploading?")
    // const urlDest = "/".concat(target, "-upload/");
    const fullURL = baseURL + `/upload?q=${target}&n=${fileName}`;
    // const headers = {
    //   "Content-type": "application/json",
    //   "X-CSRFToken": userStore.token,
      // "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value(),
    // }

    // XXX
    console.log("---> Uploading file to %s", fullURL);
    // console.log("---> File contents:\n%s", json);
    // console.log("---> File TYPE:\n%s", typeof(json));
    // console.log("XLS? >>>\n%s", JSON.stringify(xlsFile));

    // formData.append("json", json);

    const res = await fetch(fullURL, {
      method: "POST",
      // credentials: "include",
      headers: {
        "Accept": "application/json",
        // "X-CSRFToken": userStore.token,
        "Content-Encoding": "gzip",
      },
      body: fileData,
    })

    if (!res.ok) {
      // Error handling
    }

    const response = await res.json();

    console.log("---> Got response %s", JSON.stringify(response));

    return response;

    // return axiosUtlity.post(urlDest, formData, headers, {
    //   onUploadProgress
    // });
  }

}

export default new UploadFilesService();
