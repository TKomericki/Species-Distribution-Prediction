using System;
using System.Collections.Generic;
using System.Collections.Specialized;
using System.Data;
using System.Data.Odbc;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shapes;
using Microsoft.Win32;

namespace MapPredictionApp
{
    /// <summary>
    /// Interaction logic for MainWindow.xaml
    /// </summary>
    public partial class MainWindow : Window
    {
        string currentMap;
        string currentCsv = "";
        string currentZip = "";

        public MainWindow()
        {
            InitializeComponent();
        }

        private void UseDatabase(object sender, RoutedEventArgs e)
        {
            BrowseCSVButton.Visibility = Visibility.Hidden;
            OrLabel.Visibility = Visibility.Hidden;
            CsvDnDArea.Visibility = Visibility.Hidden;
            RemoveCsvButton.IsEnabled = false;
            RemoveCsvButton.Visibility = Visibility.Hidden;
            currentCsv = "";
            UpdateFiles();
            UpdateImportButton();
        }

        private void UseCsv(object sender, RoutedEventArgs e)
        {
            BrowseCSVButton.Visibility = Visibility.Visible;
            OrLabel.Visibility = Visibility.Visible;
            CsvDnDArea.Visibility = Visibility.Visible;
            RemoveCsvButton.Visibility = Visibility.Visible;
            UpdateImportButton();
        }

        private void BrowseZip(object sender, RoutedEventArgs e)
        {
            ImportResult.Text = "";

            OpenFileDialog openFileDlg = new OpenFileDialog();

            openFileDlg.DefaultExt = ".zip";
            openFileDlg.Filter = "Archive (.zip)|*.zip";

            Nullable<bool> result = openFileDlg.ShowDialog();
            if (result == true)
            {
                currentZip = openFileDlg.FileName;
                ImportButton.IsEnabled = true;
                RemoveZipButton.IsEnabled = true;
                UpdateFiles();
            }
        }

        private void BrowseCsv(object sender, RoutedEventArgs e)
        {
            ImportResult.Text = "";

            OpenFileDialog openFileDlg = new OpenFileDialog();

            openFileDlg.DefaultExt = ".csv";
            openFileDlg.Filter = "CSV File (.csv)|*.csv";

            Nullable<bool> result = openFileDlg.ShowDialog();
            if (result == true)
            {
                currentCsv = openFileDlg.FileName;
                ImportButton.IsEnabled = true;
                RemoveCsvButton.IsEnabled = true;
                UpdateFiles();
            }
        }

        private void ZipDnD_DragOver(object sender, DragEventArgs e)
        {
            DnD_DragOver(sender, e, ".zip");
        }

        private void CsvDnD_DragOver(object sender, DragEventArgs e)
        {
            DnD_DragOver(sender, e, ".csv");
        }

        private void DnD_DragOver(object sender, DragEventArgs e, string extension)
        {
            bool isValid = false;

            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                string[] files = (string[])e.Data.GetData(DataFormats.FileDrop);
                if (files.Length == 1) isValid = System.IO.Path.GetExtension(files[0]).ToLowerInvariant().Equals(extension);
            }

            if (!isValid) e.Effects = DragDropEffects.None;
            e.Handled = true;
        }

        private void ZipDnD_Drop(object sender, DragEventArgs e)
        {
            currentZip = ((string[])e.Data.GetData(DataFormats.FileDrop))[0];
            RemoveZipButton.IsEnabled = true;
            UpdateFiles();
            UpdateImportButton();
        }

        private void CsvDnD_Drop(object sender, DragEventArgs e)
        {
            currentCsv = ((string[])e.Data.GetData(DataFormats.FileDrop))[0];
            RemoveCsvButton.IsEnabled = true;
            UpdateFiles();
            UpdateImportButton();
        }

        private void ImportData(object sender, RoutedEventArgs e)
        {
            using (ZipArchive archive = ZipFile.OpenRead(currentZip))
            {
                foreach (string extension in Constants._extensions)
                {
                    if(archive.Entries.Where(s => s.Name.EndsWith(extension)).Count() == 0)
                    {
                        ImportResult.Text = "The zip file does not containt required files (*.shp, *.shx, *.dbf)";
                        ImportResult.Foreground = Brushes.Red;
                        return;
                    }
                }
            }

            if (CsvRBtn.IsChecked == true)
            {
                File.Copy(currentCsv, ParamsReader.GetParam("default_csv_name"));
            }
            else
            {
                using (OdbcConnection conn = new OdbcConnection(ParamsReader.GetParam("connection_string")))
                {
                    OdbcCommand com = new OdbcCommand(ParamsReader.GetParam("command"), conn);
                    conn.Open();
                    OdbcDataReader reader = com.ExecuteReader();
                    StringBuilder csv = new StringBuilder();
                    csv.AppendLine(reader.GetName(0) + "," + reader.GetName(1) + "," + reader.GetName(2));
                    while (reader.Read()) csv.AppendLine(reader[0] + "," + reader[1] + "," + reader[2]);

                    File.WriteAllText(ParamsReader.GetParam("default_csv_name"), csv.ToString());
                }
            }

            RpcClient client = new RpcClient();
            string[] data = client.Call("import", Constants._directoriesWorker).Split(",");
            string folder = data[0];

            if ((ParamsReader.GetParam("rabbit_host")).Equals("localhost"))
            {
                string destination = ParamsReader.GetParam("main_directory") + folder + "\\";
                File.Copy(currentZip, destination + currentZip.Split("\\").Last());
                File.Copy(ParamsReader.GetParam("default_csv_name"), destination + ParamsReader.GetParam("default_csv_name"));
            }
            else
            {
                string uploadURL = data[1];

                using (WebClient myWebClient = new WebClient())
                {
                    NameValueCollection parameters = new NameValueCollection();
                    parameters.Add("directory", folder);
                    myWebClient.QueryString = parameters;
                    myWebClient.UploadFile(uploadURL, currentZip);
                    myWebClient.UploadFile(uploadURL, ParamsReader.GetParam("default_csv_name"));
                }
            }

            string response = client.Call(folder, Constants._importWorker);

            if (!response.StartsWith(Constants._successmsg))
            {
                ImportResult.Text = "Import unsuccessful.\n";
                ImportResult.Text += response;
                ImportResult.Foreground = Brushes.Red;
            }
            else
            {
                ImportResult.Text = "Import successful.\n";
                string[] responses = response.Split(","); 
                ImportResult.Text += "Code: " + responses[1];
                ImportResult.Foreground = Brushes.Green;
            }
            client.Close();
            File.Delete(ParamsReader.GetParam("default_csv_name"));
        }

        private void RemoveZip(object sender, RoutedEventArgs e)
        {
            currentZip = "";
            ImportButton.IsEnabled = false;
            RemoveZipButton.IsEnabled = false;
            UpdateFiles();
        }

        private void RemoveCsv(object sender, RoutedEventArgs e)
        {
            currentCsv = "";
            ImportButton.IsEnabled = false;
            RemoveCsvButton.IsEnabled = false;
            UpdateFiles();
        }

        private void UpdateFiles()
        {
            FilePath.Content = "";
            if(currentZip.Length > 0) FilePath.Content = "Zip file: " + currentZip + "\n";
            if(currentCsv.Length > 0) FilePath.Content += "Csv file: " + currentCsv;
        }

        private void UpdateImportButton()
        {
            ImportButton.IsEnabled = currentZip.Length > 0 && !(CsvRBtn.IsChecked == true && currentCsv.Length == 0);
        }

        private void GetClasses(object sender, RoutedEventArgs e)
        {
            ExportResult.Text = "";
            classesPanel.Children.Clear();

            RpcClient client = new RpcClient();
            string response = client.Call(ParamsReader.GetParam("get_species_keyword") + "," + MapCode.Text, Constants._exportWorker);
            if (response.Equals("null"))
            {
                ExportResult.Text = "Unknown map code.";
                ExportResult.Foreground = Brushes.Red;
                SelectButton.IsEnabled = false;
                DeselectButton.IsEnabled = false;
                GenerateButton.IsEnabled = false;
            }
            else
            {
                foreach(string species in response.Split(","))
                {
                    CheckBox b = new CheckBox() { Content = species };
                    classesPanel.Children.Add(b);
                }
                currentMap = MapCode.Text;
                SelectButton.IsEnabled = true;
                DeselectButton.IsEnabled = true;
                GenerateButton.IsEnabled = true;
            }
        }

        private void GeneratePredictions(object sender, RoutedEventArgs e)
        {
            RpcClient client = new RpcClient();
            List<string> species = new List<string>();
            String color = "";
            foreach(RadioButton rb in ColorButtons.Children)
            {
                if (rb.IsChecked == true)
                {
                    color = rb.Content.ToString();
                    break;
                }
            }

            foreach (var child in classesPanel.Children)
            {
                if ((child as CheckBox).IsChecked == true) species.Add((child as CheckBox).Content.ToString());//classes += (child as CheckBox).Content + ";";
            }

            if (species.Count == 0)
            {
                ExportResult.Text = "Please select at least one species!";
                ExportResult.Foreground = Brushes.Red;
                return;
            }

            string[] data = client.Call("export", Constants._directoriesWorker).Split(",");
            string response = client.Call(currentMap + "," + string.Join(";", species) + "," + color + "," + data[0], Constants._exportWorker);
            client.Close();

            if (response.StartsWith(Constants._successmsg))
            {
                string relativePath = response.Split(",")[1];
                string fullPath = ParamsReader.GetParam("result_directory") + relativePath;

                if ((ParamsReader.GetParam("rabbit_host")).Equals("localhost"))
                {
                    ExportResult.Text = "Export successful.\nResult path: " + fullPath;
                }
                else
                {
                    string downloadURL = data[1];
                    Directory.CreateDirectory(ParamsReader.GetParam("result_directory") + relativePath.Split("\\")[0]);
                    using (WebClient myWebClient = new WebClient())
                    {
                        myWebClient.DownloadFile(downloadURL + relativePath, fullPath);
                    }
                    ExportResult.Text = "Export successful.\nResult path: " + fullPath + "\nDownload link: " + downloadURL + relativePath;
                }
                ExportResult.Foreground = Brushes.Green;
            }
            else
            {
                ExportResult.Text = response;
                ExportResult.Foreground = Brushes.Red;
            }
        }

        private void SelectAll(object sender, RoutedEventArgs e)
        {
            foreach (var child in classesPanel.Children) (child as CheckBox).IsChecked = true;
        }

        private void DeselectAll(object sender, RoutedEventArgs e)
        {
            foreach (var child in classesPanel.Children) (child as CheckBox).IsChecked = false;
        }
    }
}
