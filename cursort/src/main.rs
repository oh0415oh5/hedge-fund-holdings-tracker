use std::cmp::Ordering;
use std::env;
use std::fs;
use std::io::{self, BufRead, IsTerminal, Write};
use std::path::PathBuf;
use std::process;

#[derive(Debug, Default)]
struct Args {
    files: Vec<PathBuf>,
    numeric: bool,
    reverse: bool,
    unique: bool,
    ignore_blanks: bool,
    ignore_case: bool,
}

fn main() {
    if let Err(error) = run() {
        eprintln!("cursort: {error}");
        process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let args = parse_args()?;
    let mut lines = read_lines(&args)?;

    lines.sort_by(|left, right| compare_lines(left, right, &args));

    if args.unique {
        lines.dedup_by(|left, right| {
            compare_lines(left, right, &args) == Ordering::Equal
        });
    }

    let stdout = io::stdout();
    let mut handle = stdout.lock();
    for line in lines {
        writeln!(handle, "{line}").map_err(|error| error.to_string())?;
    }

    Ok(())
}

fn parse_args() -> Result<Args, String> {
    let mut args = Args::default();
    let mut iter = env::args().skip(1);

    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "-n" | "--numeric" => args.numeric = true,
            "-r" | "--reverse" => args.reverse = true,
            "-u" | "--unique" => args.unique = true,
            "-b" | "--ignore-blanks" => args.ignore_blanks = true,
            "-f" | "--ignore-case" => args.ignore_case = true,
            "-h" | "--help" => {
                print_help();
                process::exit(0);
            }
            value if value.starts_with('-') => {
                return Err(format!("unknown option `{value}`"));
            }
            value => args.files.push(PathBuf::from(value)),
        }
    }

    Ok(args)
}

fn print_help() {
    eprintln!(
        "Usage: cursort [OPTIONS] [FILE]...\n\n\
         Sort lines from files or stdin.\n\n\
         Options:\n\
           -n, --numeric         Sort numerically\n\
           -r, --reverse         Reverse sort order\n\
           -u, --unique          Suppress duplicate lines\n\
           -b, --ignore-blanks   Trim whitespace before comparing\n\
           -f, --ignore-case     Case-insensitive comparison\n\
           -h, --help            Show this help message"
    );
}

fn read_lines(args: &Args) -> Result<Vec<String>, String> {
    if args.files.is_empty() {
        return read_stdin();
    }

    let mut lines = Vec::new();
    for path in &args.files {
        let content = fs::read_to_string(path)
            .map_err(|error| format!("{}: {error}", path.display()))?;
        lines.extend(content.lines().map(str::to_owned));
    }
    Ok(lines)
}

fn read_stdin() -> Result<Vec<String>, String> {
    if io::stdin().is_terminal() {
        return Err("no input files and stdin is a terminal".to_string());
    }

    let stdin = io::stdin();
    let mut lines = Vec::new();
    for line in stdin.lock().lines() {
        lines.push(line.map_err(|error| error.to_string())?);
    }
    Ok(lines)
}

fn compare_lines(left: &str, right: &str, args: &Args) -> Ordering {
    let left_key = normalize(left, args);
    let right_key = normalize(right, args);

    let ordering = if args.numeric {
        compare_numeric(&left_key, &right_key)
    } else if args.ignore_case {
        left_key.to_lowercase().cmp(&right_key.to_lowercase())
    } else {
        left_key.cmp(&right_key)
    };

    if args.reverse {
        ordering.reverse()
    } else {
        ordering
    }
}

fn normalize(line: &str, args: &Args) -> String {
    if args.ignore_blanks {
        line.trim().to_string()
    } else {
        line.to_string()
    }
}

fn compare_numeric(left: &str, right: &str) -> Ordering {
    match (left.parse::<f64>(), right.parse::<f64>()) {
        (Ok(left_value), Ok(right_value)) => left_value
            .partial_cmp(&right_value)
            .unwrap_or(Ordering::Equal),
        (Ok(_), Err(_)) => Ordering::Less,
        (Err(_), Ok(_)) => Ordering::Greater,
        (Err(_), Err(_)) => left.cmp(right),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sorts_lexicographically() {
        let args = Args {
            files: vec![],
            numeric: false,
            reverse: false,
            unique: false,
            ignore_blanks: false,
            ignore_case: false,
        };

        assert_eq!(
            compare_lines("banana", "apple", &args),
            Ordering::Greater
        );
    }

    #[test]
    fn sorts_numerically() {
        let args = Args {
            files: vec![],
            numeric: true,
            reverse: false,
            unique: false,
            ignore_blanks: false,
            ignore_case: false,
        };

        assert_eq!(compare_lines("10", "2", &args), Ordering::Greater);
    }
}
