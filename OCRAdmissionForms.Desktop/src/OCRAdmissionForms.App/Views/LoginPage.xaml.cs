using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using OCRAdmissionForms.Core.Services;

namespace OCRAdmissionForms.App.Views;

public partial class LoginPage : Page
{
    private readonly AuthService _authService;

    public LoginPage()
    {
        InitializeComponent();
        _authService = new AuthService();
        
        // Focus username field and initialize on load
        Loaded += async (s, e) => 
        {
            TxtUsername.Focus();
            try 
            {
                await _authService.EnsureDefaultAdminAsync();
            }
            catch (Exception ex)
            {
                ShowError($"Database error: {ex.Message}\nPlease restart the app.");
            }
        };
        
        // Enter key to login
        TxtPassword.KeyDown += (s, e) =>
        {
            if (e.Key == Key.Enter) Login_Click(s, e);
        };
    }



    private async void Login_Click(object sender, RoutedEventArgs e)
    {
        // Validate inputs
        if (string.IsNullOrWhiteSpace(TxtUsername.Text))
        {
            ShowError("Please enter your username");
            TxtUsername.Focus();
            return;
        }

        if (string.IsNullOrWhiteSpace(TxtPassword.Password))
        {
            ShowError("Please enter your password");
            TxtPassword.Focus();
            return;
        }

        // Disable button and show loading
        BtnLogin.IsEnabled = false;
        BtnLogin.Content = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            Children =
            {
                new System.Windows.Controls.TextBlock { Text = "Signing in...", FontSize = 15 }
            }
        };

        try
        {
            var result = await _authService.LoginAsync(TxtUsername.Text, TxtPassword.Password);

            if (result.Success)
            {
                // Show offline indicator if logged in offline
                if (result.IsOffline)
                {
                    OfflinePanel.Visibility = Visibility.Visible;
                    await Task.Delay(1500);
                }

                // Navigate to main window
                if (Application.Current.MainWindow is MainWindow mainWindow)
                {
                    // Update user info in sidebar
                    mainWindow.TxtUserName.Text = result.User?.FullName ?? "User";
                    mainWindow.TxtUserRole.Text = result.User?.Role.ToString() ?? "Staff";
                    
                    // Navigate to dashboard
                    mainWindow.ContentFrame.Navigate(new DashboardPage());
                }
            }
            else
            {
                ShowError(result.Error ?? "Login failed");
                
                if (result.IsOffline)
                {
                    OfflinePanel.Visibility = Visibility.Visible;
                }
            }
        }
        catch (System.Exception ex)
        {
            ShowError($"Error: {ex.Message}");
        }
        finally
        {
            // Reset button
            BtnLogin.IsEnabled = true;
            BtnLogin.Content = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                Children =
                {
                    new ModernWpf.Controls.SymbolIcon { Symbol = ModernWpf.Controls.Symbol.Contact },
                    new System.Windows.Controls.TextBlock { Text = "Sign In", FontSize = 15, Margin = new Thickness(8, 0, 0, 0) }
                }
            };
        }
    }

    private void ShowError(string message)
    {
        TxtError.Text = message;
        ErrorPanel.Visibility = Visibility.Visible;
    }
}
