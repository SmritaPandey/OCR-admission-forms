using System.Windows.Data;
using System.Globalization;

namespace OCRAdmissionForms.App.Converters;

public class BoolToActiveConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
    {
        return value is bool b && b ? "Active" : "Inactive";
    }

    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
    {
        return value?.ToString() == "Active";
    }
}
