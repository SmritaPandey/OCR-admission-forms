using System.Collections.Generic;
using System.IO;
using OCRAdmissionForms.Core.Entities;

namespace OCRAdmissionForms.Core.Interfaces;

public interface IExcelService
{
    byte[] ExportAdmissionForms(IEnumerable<AdmissionForm> forms);
    IEnumerable<AdmissionForm> ImportAdmissionForms(Stream excelStream);
}
