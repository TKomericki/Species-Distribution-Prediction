using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace MapPredictionApp
{
    static class ParamsReader
    {
        public static string GetParam(string key)
        {
            var values = JsonConvert.DeserializeObject<Dictionary<string, dynamic>>(File.ReadAllText("..\\..\\..\\params.json"));
            return (string)values[key];
        }
    }
}
