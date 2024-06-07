<!-- 
    Adopted liberally from:
    https://github.com/bezkoder/vuetify-file-upload
 -->
 <template>
    <div class="text-center">
      <div>
        <div>
          <v-progress-linear
            v-model="progress"
            color="light-blue"
            height="25"
            reactive
          >
            <strong>{{ progress }} %</strong>
          </v-progress-linear>
        </div>
      </div>
  
      <!-- <v-row no-gutters justify="center" align="center"> -->
        <!-- <v-col cols="8"> -->
        <!-- <v-col> -->
            <!--
                See `rules` for filtering on file type. 
                Not super critical at present. 
             -->
          <v-file-input
            show-size
            label="Select MZID file(s)"
            type="File"
            v-model="files"
            multiple
          ></v-file-input>
          <!-- v-model="currentFile" -->
        <!-- </v-col> -->
        <!--
            This appears to break when invoked using Vuetify auto-magic 
            @change="selectFile($event)" 
        -->
            
        <!-- <v-col cols="4" class="pl-2"> -->
        <v-container>
        <v-row>
            <!-- color="primary" -->
          <v-btn 
            :key="uploadSuccess" 
            @click="importFilesAndSubmit" 
            v-if="!uploadSuccess">
            Upload Selected Files
            <!-- <v-icon right dark>mdi-cloud-upload</v-icon> -->
          </v-btn>
        <!-- <v-col>
          <v-btn right color="success" dark small @click="upload">
            Submit & Analyze
          </v-btn>
        </v-col> -->
      </v-row>
      <v-row>
        <v-btn @click="analyzeFiles()">
            Analyze files
        </v-btn>
      </v-row>
    </v-container>
      <!-- </v-row> -->
      <v-container>
      <v-alert v-if="message" color="blue-grey" class="pa-5" dark>
        {{ message }}
      </v-alert>
      <v-data-table
        v-if="processedResult"
        :headers="tableHeaders"
        :items="processedResult"
        item-key="UniProtAcc"
      >

      </v-data-table>
        <!-- <v-btn @click="forceRedraw()">Redraw!</v-btn> -->
    </v-container>
    </div>
  </template>
  
  <script>

import UploadService from "@/components/UploadService";

const baseURL = import.meta.env.DEV ? import.meta.env.VITE_DEV_MIDDLEWARE_BASE + '/api': "/api";

  export default {
    name: "upload-files",
    props: {
        uploadTargetURL: String,
    },
    components: { },
    data() {
      return {
        files: [],
        readers: [],
        standIn: false,
        progress: 0,
        message: "Data must be selected before results are available",
        tableHeaders: [
          {title: "UniProt Accession", align: "center", value: "UniProtAcc"},
          {title: "Amino Acid Position", align: "center", value: "AAPosition"},
          {title: "Distinct Peptide Count", align: "center", value: "DistinctPeptideCount"},
          {title: "Spectral Count", align: "center", value: "SpectralCount"},
          {title: "Peptides", align: "center", value: "Peptides"},
      ],
        processedResult: null,
        showChart: false,
        uploadSuccess: false,
        counterToken: 0,
      };
    },
    methods: {
        forceRedraw() {
          this.counterToken += 1;
        },
        async analyzeFiles() {
            this.message = "Analyzing..."
            const analysisURL = baseURL + "/standalone-analyze"
            const response = await fetch(analysisURL)
            if (!response.ok) {
                // Error handling
            }
            const result = await response.json();
            this.message = "Results available"
            if (result.error) {
              // TODO Error handling
            }
            this.processedResult = result.results
          },
        importFilesAndSubmit() {
            if (!this.files) {
                this.message = "Please select file(s) for upload!"
                return;
            }
            // See e.g. https://www.codeply.com/p/1K7sf12k0k / https://stackoverflow.com/a/60815138
            this.files.forEach((file, f) => {
                console.log("File name? %s", file.name);
                this.readers[f] = new FileReader();
                this.readers[f].onloadend = (e) => {
                    let fileData = this.readers[f].result;
                    // console.log("Found data: %s", JSON.stringify(fileData));
                    this.upload(file.name, fileData);
                }
                this.readers[f].readAsDataURL(this.files[f])
            })
        },
  
      upload(fileName, fileData) {
  
        UploadService.upload(fileName, fileData, this.uploadTargetURL, (event) => {
          this.progress = Math.round((100 * event.loaded) / event.total);
        })
          .then((response) => {
            // this.message = response.data.message;
            this.message = response.result ? response.result : response.error;
            if (response.plot) {
              this.chartData = JSON.parse(response.plot);
            }
            else if (response.image) {
              this.imageData = "data:image/png; base64, " + response.image;
              // console.log("Image data is now: %s", this.imageData)
            }
            else {
              this.standIn = true;
            }
            this.showChart = true;
            return true;
          })
          .catch(() => {
            this.progress = 0;
            this.message = "Could not upload the file!";
            // this.currentFile = null;
            // this.data = null;
            return false;
          });
      },
    },
  };

  </script>